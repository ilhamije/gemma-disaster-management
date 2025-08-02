import json
import uuid
import math
import time
import logging

from datetime import datetime
from pathlib import Path
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded, Retry
from PIL import Image
from PIL.ExifTags import TAGS
import requests
from shapely.geometry import shape
from shapely.geometry.polygon import orient


from .core.metadata_process import get_exif_data, extract_lat_lon, create_circle_polygon

from .core.gemma_client import OllamaGemmaClient
from .models import db, AnalysisResult, PolygonFeature, PolygonJSON

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@shared_task(bind=True, soft_time_limit=600, time_limit=720, max_retries=3)
def analyze_image_task(self, image_path: str, batch_id: str = ""):
    result = None
    try:
        gemma_client = OllamaGemmaClient()
        self.update_state(state='PROGRESS', meta={'status': 'Starting image analysis...'})

        # Create DB entry
        result = AnalysisResult(
            batch_id=batch_id,
            image_filename=Path(image_path).name,
            processing_status="processing"
        )
        db.session.add(result)
        db.session.commit()

        # --- Gemma AI inference ---
        logger.info(f"Starting analysis for {image_path}")
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Calling Ollama API...'})
            response = gemma_client.analyze_disaster_image(image_path)
            logger.info(f"Ollama request completed for {image_path}")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            _handle_error(result, f"Ollama API error: {e}")
            raise self.retry(countdown=60, exc=e)
        except SoftTimeLimitExceeded:
            _handle_error(result, "Soft time limit exceeded")
            raise
        except Exception as e:
            _handle_error(result, f"Unexpected Ollama error: {e}")
            raise

        features = response.get("features", [])
        if not features:
            _handle_error(result, "No features found in response")
            raise ValueError("No features found in response")

        # Compute center of polygons (fallback if EXIF fails)
        # center_lat, center_lon = calculate_centroid(features)
        # result.center_lat = center_lat
        # result.center_lon = center_lon

        try:
            image = Image.open(image_path)
            exif = get_exif_data(image)
            lat, lon = extract_lat_lon(exif)
            if lat is not None and lon is not None:
                center_lat, center_lon = lat, lon   # <-- Use EXIF GPS here!
            else:
                center_lat, center_lon = calculate_centroid(features)  # Fallback
        except Exception as e:
            logger.warning(f"Could not extract EXIF GPS: {e}")
            center_lat, center_lon = calculate_centroid(features)
        result.center_lat = center_lat
        result.center_lon = center_lon

        # Process Gemma polygons only
        polygons = []
        for i, feat in enumerate(features):
            try:
                props = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [])
                if not coords:
                    logger.warning(f"Empty coordinates for feature {i}")
                    continue

                # Transform to map coordinates (approx from image space)
                transformed_coords = transform_coordinates_to_geo(coords, center_lat, center_lon, image_path)
                polygons.append(
                    PolygonFeature(
                        polygon_id=props.get("id", f"poly_{i}"),
                        damage_type=props.get("damage_type", "unknown"),
                        confidence=float(props.get("confidence", 0.0)),
                        class_label=props.get("class", ""),
                        notes=props.get("notes", ""),
                        coordinates=json.dumps(transformed_coords)
                    )
                )
            except Exception as e:
                logger.error(f"Error processing feature {i}: {e}")
                continue

        result.polygons = polygons
        result.processing_status = "completed"
        db.session.commit()
        logger.info(f"Analysis completed: {len(polygons)} polygons processed")

        # Update combined polygons for map
        update_combined_polygons(batch_id)

        # Trigger map update event
        trigger_map_update.delay(batch_id)

        return {"status": "completed", "result_id": result.id,
                "batch_id": batch_id, "polygons_count": len(polygons)}

    except SoftTimeLimitExceeded:
        _handle_error(result, "Processing time limit exceeded")
        raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


def _handle_error(result, message):
    logger.error(message)
    if result:
        result.processing_status = "failed"
        result.error_message = message
        db.session.commit()


def extract_gps_coordinates(image_path):
    try:
        with Image.open(image_path) as image:
            exifdata = image.getexif()
            if exifdata:
                for tag_id in exifdata:
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "GPSInfo":
                        gps_data = exifdata[tag_id]
                        if 2 in gps_data and 4 in gps_data:
                            lat = convert_to_degrees(gps_data[2])
                            lon = convert_to_degrees(gps_data[4])
                            if gps_data.get(1) == 'S': lat = -lat
                            if gps_data.get(3) == 'W': lon = -lon
                            return lat, lon
    except Exception as e:
        logger.error(f"Error extracting GPS from {image_path}: {e}")
    return None


def convert_to_degrees(value):
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            return float(value[0]) + float(value[1]) / 60.0 + float(value[2]) / 3600.0
        return float(value) if value else 0.0
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting GPS degrees: {e}")
        return 0.0


def calculate_centroid(features):
    try:
        lat_list, lon_list = [], []
        for feat in features:
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            gtype = geom.get("type")
            if gtype == "Polygon" and coords and isinstance(coords[0], list) and len(coords[0]) > 0:
                lon, lat = coords[0][0]
            elif gtype == "LineString" and coords and len(coords) > 0:
                lon, lat = coords[0]
            elif gtype == "Point" and coords and len(coords) == 2:
                lon, lat = coords
            else:
                continue
            lon_list.append(lon)
            lat_list.append(lat)
        if lon_list and lat_list:
            return sum(lat_list) / len(lat_list), sum(lon_list) / len(lon_list)
    except Exception as e:
        logger.warning(f"Error calculating centroid: {e}")
    return 0.0, 0.0


def is_valid_latlon(lat, lon):
    return -90 <= lat <= 90 and -180 <= lon <= 180


def transform_coordinates_to_geo(coords, center_lat, center_lon, image_path):
    original_width = 4000
    # resize_width = 512
    FLIGHT_ALTITUDE_M = 120
    SENSOR_WIDTH_MM = 6.3
    FOCAL_LENGTH_MM = 4.73
    GSD_fullres = (SENSOR_WIDTH_MM * FLIGHT_ALTITUDE_M) / (FOCAL_LENGTH_MM * original_width)
    # meters_per_pixel = GSD_fullres * (original_width / resize_width)
    meters_per_pixel = GSD_fullres


    # If the center is 0,0 we assume Gemma already outputs relative offsets near 0,0
    if center_lat == 0.0 and center_lon == 0.0:
        return coords  # keep Gemma's output as-is (already normalized)

    try:
        with Image.open(image_path) as img:
            original_width, original_height = img.size

        transformed_coords = []
        for coord_ring in coords:
            transformed_ring = []
            for coord_pair in coord_ring:
                if len(coord_pair) >= 2:
                    pixel_x, pixel_y = float(coord_pair[0]), float(coord_pair[1])
                    dx_meters = (pixel_x - original_width / 2) * meters_per_pixel
                    dy_meters = (pixel_y - original_height / 2) * meters_per_pixel
                    lat_offset = dy_meters / 111320.0
                    lon_offset = dx_meters / (111320.0 * math.cos(math.radians(center_lat)))
                    transformed_ring.append([center_lon + lon_offset, center_lat + lat_offset])
            transformed_coords.append(transformed_ring)
        return transformed_coords
    except Exception as e:
        logger.error(f"Error transforming coordinates for {image_path}: {e}")
        return coords


def normalize_polygon(coords):
    """Ensure polygon follows GeoJSON spec: closed ring, wrapped list."""
    if not coords:
        return [[[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]]
    if coords and isinstance(coords[0][0], (int, float)):
        coords = [coords]
    if coords[0][0] != coords[0][-1]:
        coords[0].append(coords[0][0])
    return coords


def update_combined_polygons(batch_id):
    from datetime import datetime
    try:
        # Query polygon features for this batch
        polys = (
            db.session.query(PolygonFeature)
            .join(AnalysisResult)
            .filter(AnalysisResult.batch_id == batch_id)
            .all()
        )

        features = []
        for p in polys:
            try:
                coords = normalize_polygon(json.loads(p.coordinates))
                poly_shape = shape({"type": "Polygon", "coordinates": coords})
                if not poly_shape.is_valid or poly_shape.is_empty:
                    logger.warning(f"Skipping invalid polygon id={p.id}")
                    continue

                poly_shape = orient(poly_shape, sign=1.0)
                coords = [list(poly_shape.exterior.coords)]

                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": p.polygon_id,
                        "damage_type": p.damage_type,
                        "class": p.class_label,
                        "confidence": p.confidence,
                        "notes": p.notes,
                        "created_at": p.created_at.isoformat()
                    },
                    "geometry": {"type": "Polygon", "coordinates": coords}
                })
            except Exception as e:
                logger.error(f"Failed to process polygon {p.id}: {e}")
                continue

        geojson = {"type": "FeatureCollection", "features": features}

        # Calculate centroid from all image EXIF centers (from AnalysisResult for this batch)
        results = db.session.query(AnalysisResult).filter_by(batch_id=batch_id).all()
        centers = [(r.center_lat, r.center_lon) for r in results
                   if r.center_lat is not None and r.center_lon is not None]
        if centers:
            center_lat = sum(pt[0] for pt in centers) / len(centers)
            center_lon = sum(pt[1] for pt in centers) / len(centers)
            geojson["properties"] = {
                "center_lat": center_lat,
                "center_lon": center_lon
            }

        # Update or add to PolygonJSON table
        existing = PolygonJSON.query.filter_by(name="latest").first()
        if existing:
            existing.geojson = json.dumps(geojson)
            existing.created_at = datetime.utcnow()
        else:
            db.session.add(PolygonJSON(name="latest", geojson=json.dumps(geojson)))
        db.session.commit()
        logger.info(f"PolygonJSON updated: {len(features)} features")
    except Exception as e:
        logger.error(f"Error updating combined polygons: {e}")
        db.session.rollback()


@shared_task(bind=True, soft_time_limit=60, time_limit=120)
def trigger_map_update(self, batch_id):
    try:
        from flask import current_app
        from sqlalchemy import select
        with current_app.app_context():
            results = db.session.scalars(
                select(AnalysisResult).filter_by(batch_id=batch_id, processing_status="completed")
            ).all()

            if results:
                batch_summary = {
                    "batch_id": batch_id,
                    "completed_count": len(results),
                    "total_polygons": sum(len(r.polygons) for r in results),
                    "last_updated": datetime.now().isoformat(),
                    "status": "updated"
                }
                update_batch_status(batch_id, batch_summary)
                logger.info(f"Map update triggered for batch {batch_id}: {len(results)} results processed")
                return {"status": "success", "batch_id": batch_id, "results_count": len(results)}
            else:
                logger.info(f"No completed results found for batch {batch_id}")
                return {"status": "no_results", "batch_id": batch_id}
    except Exception as e:
        logger.error(f"Error triggering map update for batch {batch_id}: {e}")
        self.update_state(state='FAILURE', meta={
            'status': f'Map update failed: {str(e)}',
            'error_type': type(e).__name__,
            'batch_id': batch_id
        })
        return {"status": "error", "batch_id": batch_id, "error": str(e)}


def update_batch_status(batch_id, status_data):
    try:
        from pathlib import Path
        status_dir = Path("batch_status")
        status_dir.mkdir(exist_ok=True)
        status_file = status_dir / f"{batch_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        logger.info(f"Batch status updated: {status_file}")
    except Exception as e:
        logger.error(f"Error updating batch status: {e}")
