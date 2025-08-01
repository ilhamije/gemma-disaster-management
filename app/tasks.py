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
from PIL.ExifTags import TAGS, GPSTAGS
import requests

from .core.gemma_client import OllamaGemmaClient
from .models import db, AnalysisResult, PolygonFeature

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@shared_task(bind=True, soft_time_limit=600, time_limit=720, max_retries=3)
def analyze_image_task(self, image_path: str, batch_id: str = ""):
    """
    Analyze disaster image with proper timeout and error handling
    """
    result = None

    try:
        gemma_client = OllamaGemmaClient()
        self.update_state(state='PROGRESS', meta={'status': 'Starting image analysis...'})

        # Create database record
        result = AnalysisResult(
            batch_id=batch_id,
            image_filename=Path(image_path).name,
            processing_status="processing"
        )
        db.session.add(result)
        db.session.commit()

        logger.info(f"Starting analysis for {image_path}")
        start_time = time.time()

        # Call Ollama with timeout handling
        try:
            self.update_state(state='PROGRESS', meta={'status': 'Calling Ollama API...'})
            response = gemma_client.analyze_disaster_image(image_path)

            duration = time.time() - start_time
            logger.info(f"Ollama request completed in {duration:.2f}s for {image_path}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama timeout after {time.time() - start_time:.2f}s for {image_path}")
            result.processing_status = "failed"
            result.error_message = f"Ollama API timeout: {str(e)}"
            db.session.commit()

            countdown = 2 ** self.request.retries * 60  # exponential backoff
            raise self.retry(countdown=countdown, max_retries=3, exc=e)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama connection error for {image_path}: {e}")
            result.processing_status = "failed"
            result.error_message = f"Ollama connection error: {str(e)}"
            db.session.commit()

            raise self.retry(countdown=60, max_retries=2, exc=e)

        except SoftTimeLimitExceeded:
            logger.error(f"Soft time limit exceeded for {image_path}")
            if result:
                result.processing_status = "failed"
                db.session.commit()
            raise

        except Exception as e:
            logger.error(f"Unexpected error calling Ollama for {image_path}: {type(e).__name__}: {e}")
            if result:
                result.processing_status = "failed"
                db.session.commit()
            raise

        # Process response directly (gemma_client already validated geometry)
        features = response.get("features", [])

        if not features:
            if result:
                result.processing_status = "failed"
                db.session.commit()
            raise ValueError("No features found in response")

        self.update_state(state='PROGRESS', meta={'status': 'Processing GPS coordinates...'})

        # Extract EXIF GPS data for proper geo-referencing
        gps_coords = extract_gps_coordinates(image_path)
        if gps_coords:
            center_lat, center_lon = gps_coords
            logger.info(f"GPS coordinates found: {center_lat}, {center_lon}")
        else:
            try:
                lat_list = []
                lon_list = []
                for feat in features:
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    gtype = geom.get("type")

                    if gtype == "Polygon" and coords and isinstance(coords[0], list) and len(coords[0]) > 0:
                        # use first vertex of outer ring
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
                    center_lon = sum(lon_list) / len(lon_list)
                    center_lat = sum(lat_list) / len(lat_list)
                    logger.info(f"Using calculated centroid: {center_lat}, {center_lon}")
                else:
                    center_lat, center_lon = 0.0, 0.0
                    logger.warning("No valid coordinates for centroid calculation, using defaults")
            except Exception as e:
                logger.warning(f"Error calculating centroid, using defaults: {e}")
                center_lat, center_lon = 0.0, 0.0


        result.center_lat = center_lat
        result.center_lon = center_lon

        self.update_state(state='PROGRESS', meta={'status': 'Processing polygon features...'})

        # Process polygons with proper coordinate transformation
        polygons = []
        for i, feat in enumerate(features):
            try:
                prop = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [])

                if not coords:
                    logger.warning(f"Empty coordinates for feature {i}")
                    continue

                transformed_coords = transform_coordinates_to_geo(coords, center_lat, center_lon, image_path)

                polygon = PolygonFeature(
                    polygon_id=prop.get("id", f"poly_{i}"),
                    damage_type=prop.get("damage_type", "unknown"),
                    confidence=float(prop.get("confidence", 0.0)),
                    class_label=prop.get("class", ""),
                    notes=prop.get("notes", ""),
                    coordinates=json.dumps(transformed_coords)
                )
                polygons.append(polygon)

            except Exception as e:
                logger.error(f"Error processing feature {i}: {e}")
                continue

        result.polygons = polygons
        result.processing_status = "completed"
        db.session.commit()

        logger.info(f"Analysis completed for {image_path}: {len(polygons)} polygons processed")

        # Trigger map update for this batch
        trigger_map_update.delay(batch_id)

        return {
            "status": "completed",
            "result_id": result.id,
            "batch_id": batch_id,
            "polygons_count": len(polygons)
        }

    except SoftTimeLimitExceeded as e:
        logger.error(f"Task soft time limit exceeded for {image_path}")
        if result:
            result.processing_status = "failed"
            result.error_message = "Processing time limit exceeded"
            db.session.commit()
        self.update_state(state='FAILURE', meta={'status': 'Task timed out', 'error': 'Processing time limit exceeded'})
        raise

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


def extract_gps_coordinates(image_path):
    """Extract GPS coordinates from image EXIF data"""
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
                            if gps_data.get(1) == 'S':
                                lat = -lat
                            if gps_data.get(3) == 'W':
                                lon = -lon
                            return lat, lon
    except Exception as e:
        logger.error(f"Error extracting GPS from {image_path}: {e}")
    return None


def convert_to_degrees(value):
    """Convert GPS coordinate from degrees/minutes/seconds to decimal degrees"""
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            degrees = float(value[0])
            minutes = float(value[1]) / 60.0
            seconds = float(value[2]) / 3600.0
            return degrees + minutes + seconds
        return float(value) if value else 0.0
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting GPS degrees: {e}")
        return 0.0


def transform_coordinates_to_geo(coords, center_lat, center_lon, image_path):
    """
    Transform polygon coordinates to proper geographic coordinates
    based on image center and estimated scale
    """
    try:
        with Image.open(image_path) as img:
            original_width, original_height = img.size

        transformed_coords = []
        for coord_ring in coords:
            transformed_ring = []
            for coord_pair in coord_ring:
                if len(coord_pair) >= 2:
                    pixel_x, pixel_y = float(coord_pair[0]), float(coord_pair[1])
                    meters_per_pixel = 0.5
                    dx_meters = (pixel_x - original_width / 2) * meters_per_pixel
                    dy_meters = (pixel_y - original_height / 2) * meters_per_pixel
                    lat_offset = dy_meters / 111320.0
                    lon_offset = dx_meters / (111320.0 * math.cos(math.radians(center_lat)))
                    new_lat = center_lat + lat_offset
                    new_lon = center_lon + lon_offset
                    transformed_ring.append([new_lon, new_lat])
                else:
                    transformed_ring.append(coord_pair)
            transformed_coords.append(transformed_ring)

        return transformed_coords

    except Exception as e:
        logger.error(f"Error transforming coordinates for {image_path}: {e}")
        return coords


@shared_task(bind=True, soft_time_limit=60, time_limit=120)
def trigger_map_update(self, batch_id):
    """
    Trigger frontend map update by updating batch status and notifying clients
    """
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
        logger.error(f"Error triggering map update for batch {batch_id}: {type(e).__name__}: {e}")
        self.update_state(state='FAILURE', meta={
            'status': f'Map update failed: {str(e)}',
            'error_type': type(e).__name__,
            'batch_id': batch_id
        })
        return {"status": "error", "batch_id": batch_id, "error": str(e)}


def update_batch_status(batch_id, status_data):
    """Update batch status for frontend polling"""
    try:
        from pathlib import Path
        import json

        status_dir = Path("batch_status")
        status_dir.mkdir(exist_ok=True)

        status_file = status_dir / f"{batch_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)

        logger.info(f"Batch status updated: {status_file}")

    except Exception as e:
        logger.error(f"Error updating batch status: {e}")


@shared_task(bind=True, soft_time_limit=30, time_limit=60)
def trigger_map_update_websocket(self, batch_id):
    """
    Alternative implementation using WebSocket for real-time updates
    Requires Flask-SocketIO
    """
    try:
        from flask_socketio import emit
        from flask import current_app

        with current_app.app_context():
            emit('batch_update', {
                'batch_id': batch_id,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True, namespace='/map_updates')

            logger.info(f"WebSocket update sent for batch {batch_id}")
            return {"status": "websocket_sent", "batch_id": batch_id}

    except Exception as e:
        logger.error(f"Error sending WebSocket update: {type(e).__name__}: {e}")
        self.update_state(state='FAILURE', meta={
            'status': f'WebSocket update failed: {str(e)}',
            'error_type': type(e).__name__,
            'batch_id': batch_id
        })
        return {"status": "websocket_error", "batch_id": batch_id, "error": str(e)}
