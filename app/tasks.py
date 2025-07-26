import json
import uuid
from datetime import datetime
from pathlib import Path
from celery import shared_task
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from .core.gemma_client import OllamaGemmaClient
from .models import db, AnalysisResult, PolygonFeature

@shared_task(bind=True)
def analyze_image_task(self, image_path: str, batch_id: str = ""):
    gemma_client = OllamaGemmaClient()
    self.update_state(state='PROGRESS', meta={'status': 'Starting image analysis...'})

    try:
        # Update status to processing
        result = AnalysisResult(
            batch_id=batch_id,
            image_filename=Path(image_path).name,
            processing_status="processing"
        )
        db.session.add(result)
        db.session.commit()

        response = gemma_client.analyze_disaster_image(image_path)
        features = response.get("features", [])

        if not features:
            result.processing_status = "failed"
            db.session.commit()
            raise ValueError("No features found in response")

        # Extract EXIF GPS data for proper geo-referencing
        gps_coords = extract_gps_coordinates(image_path)
        if gps_coords:
            center_lat, center_lon = gps_coords
        else:
            # Fallback to polygon centroid calculation
            lat_sum = sum(feat["geometry"]["coordinates"][0][0][1] for feat in features)
            lon_sum = sum(feat["geometry"]["coordinates"][0][0][0] for feat in features)
            center_lat = lat_sum / len(features) if features else 0.0
            center_lon = lon_sum / len(features) if features else 0.0

        result.center_lat = center_lat
        result.center_lon = center_lon
        result.processing_status = "completed"

        # Process polygons with proper coordinate transformation
        polygons = []
        for feat in features:
            prop = feat["properties"]
            coords = feat["geometry"]["coordinates"]

            # Transform coordinates based on image metadata and scale
            transformed_coords = transform_coordinates_to_geo(coords, center_lat, center_lon, image_path)

            polygons.append(PolygonFeature(
                polygon_id=prop.get("id", ""),
                damage_type=prop.get("damage_type", ""),
                confidence=prop.get("confidence", 0.0),
                class_label=prop.get("class", ""),
                notes=prop.get("notes", ""),
                coordinates=json.dumps(transformed_coords)
            ))

        result.polygons = polygons
        db.session.commit()

        # Trigger map update for this batch
        print("Calling Ollama for", image_path)
        trigger_map_update.delay(batch_id)

        return {"status": "completed", "result_id": result.id, "batch_id": batch_id}
    except Exception as e:
        if 'result' in locals():
            result.processing_status = "failed"
            db.session.commit()
        self.update_state(state='FAILURE', meta={'status': f"Analysis failed: {str(e)}"})
        raise

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
                        # Convert GPS data to decimal degrees
                        if 2 in gps_data and 4 in gps_data:
                            lat = convert_to_degrees(gps_data[2])
                            lon = convert_to_degrees(gps_data[4])
                            if gps_data.get(1) == 'S': lat = -lat
                            if gps_data.get(3) == 'W': lon = -lon
                            return lat, lon
    except Exception as e:
        print(f"Error extracting GPS: {e}")
    return None

def convert_to_degrees(value):
    """Convert GPS coordinate from degrees/minutes/seconds to decimal degrees"""
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        degrees = float(value[0])
        minutes = float(value[1]) / 60.0
        seconds = float(value[2]) / 3600.0
        return degrees + minutes + seconds
    return float(value) if value else 0.0

def transform_coordinates_to_geo(coords, center_lat, center_lon, image_path):
    """
    Transform polygon coordinates to proper geographic coordinates
    based on image center and estimated scale
    """
    try:
        # Get image dimensions for scale calculation
        with Image.open(image_path) as img:
            original_width, original_height = img.size

        # Assume the model coordinates are in a normalized space (0-1 or pixel coordinates)
        # We need to convert them to geographic coordinates around the center point

        transformed_coords = []
        for coord_ring in coords:
            transformed_ring = []
            for coord_pair in coord_ring:
                if len(coord_pair) >= 2:
                    # Assuming coords are in pixel space, convert to geographic offset
                    pixel_x, pixel_y = coord_pair[0], coord_pair[1]

                    # Convert pixel offset to meters (rough estimation)
                    # Assume 1 pixel = 0.5 meters at ground level for UAV imagery
                    meters_per_pixel = 0.5

                    # Calculate geographic offset
                    dx_meters = (pixel_x - original_width/2) * meters_per_pixel
                    dy_meters = (pixel_y - original_height/2) * meters_per_pixel

                    # Convert meters to degrees
                    lat_offset = dy_meters / 111320.0  # ~111320 meters per degree latitude
                    lon_offset = dx_meters / (111320.0 * math.cos(math.radians(center_lat)))

                    # Apply offset to center coordinates
                    new_lat = center_lat + lat_offset
                    new_lon = center_lon + lon_offset

                    transformed_ring.append([new_lon, new_lat])
                else:
                    # Keep original if malformed
                    transformed_ring.append(coord_pair)

            transformed_coords.append(transformed_ring)

        return transformed_coords

    except Exception as e:
        print(f"Error transforming coordinates: {e}")
        # Return original coordinates if transformation fails
        return coords

@shared_task
def trigger_map_update(batch_id):
    """
    Trigger frontend map update by updating batch status and notifying clients
    """
    try:
        from flask import current_app
        from sqlalchemy import select

        # Get completed results for this batch
        with current_app.app_context():
            results = db.session.scalars(
                select(AnalysisResult)
                .filter_by(batch_id=batch_id, processing_status="completed")
            ).all()

            # Update batch completion status
            if results:
                batch_summary = {
                    "batch_id": batch_id,
                    "completed_count": len(results),
                    "total_polygons": sum(len(r.polygons) for r in results),
                    "last_updated": datetime.now().isoformat(),
                    "status": "updated"
                }

                # Store batch update status (could be Redis, database flag, or file)
                # For simplicity, we'll use a simple flag mechanism
                update_batch_status(batch_id, batch_summary)

                print(f"Map update triggered for batch {batch_id}: {len(results)} results processed")
                return {"status": "success", "batch_id": batch_id, "results_count": len(results)}
            else:
                print(f"No completed results found for batch {batch_id}")
                return {"status": "no_results", "batch_id": batch_id}

    except Exception as e:
        print(f"Error triggering map update for batch {batch_id}: {e}")
        return {"status": "error", "batch_id": batch_id, "error": str(e)}

def update_batch_status(batch_id, status_data):
    """
    Update batch status for frontend polling
    This can be implemented using Redis, database flags, or simple file storage
    """
    try:
        # Simple file-based approach for development
        # In production, consider using Redis or database flags
        from pathlib import Path
        import json

        status_dir = Path("batch_status")
        status_dir.mkdir(exist_ok=True)

        status_file = status_dir / f"{batch_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)

        print(f"Batch status updated: {status_file}")

    except Exception as e:
        print(f"Error updating batch status: {e}")

# Alternative WebSocket-based implementation for real-time updates
@shared_task
def trigger_map_update_websocket(batch_id):
    """
    Alternative implementation using WebSocket for real-time updates
    Requires Flask-SocketIO
    """
    try:
        from flask_socketio import emit
        from flask import current_app

        with current_app.app_context():
            # Emit update event to all connected clients
            emit('batch_update', {
                'batch_id': batch_id,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True, namespace='/map_updates')

            print(f"WebSocket update sent for batch {batch_id}")
            return {"status": "websocket_sent", "batch_id": batch_id}

    except Exception as e:
        print(f"Error sending WebSocket update: {e}")
        return {"status": "websocket_error", "batch_id": batch_id, "error": str(e)}
