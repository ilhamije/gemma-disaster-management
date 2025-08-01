import os
import json
from flask import Blueprint, jsonify
from sqlalchemy import select, desc
from ..extensions import db
from ..models import AnalysisResult

bp = Blueprint('polygons', __name__)

@bp.route('/api/polygons', methods=['GET'])
def get_polygons():
    # Get latest result (completed or not)
    result = db.session.scalars(
        select(AnalysisResult)
        .order_by(desc(AnalysisResult.created_at))
        .limit(1)
    ).first()

    features = []

    if result:
        print('--'*20)
        print('this 1')
        # Always add center if available
        if result.center_lon is not None and result.center_lat is not None:
            print('this 1.1')
            features.append({
                "type": "Feature",
                "properties": {
                    "id": f"center_{result.id}",
                    "class": "center",
                    "waiting": result.processing_status != "completed"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [result.center_lon, result.center_lat]
                }
            })
        print('--'*20)

        print('--'*20)
        print('this 2')
        print(result)
        # If the latest result is completed, add polygons from DB
        if result.processing_status == "completed":
            print('this 2.1')
            for poly in result.polygons:
                polygon_coords = json.loads(poly.coordinates)
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": poly.polygon_id,
                        "damage_type": poly.damage_type,
                        "confidence": poly.confidence,
                        "class": poly.class_label,
                        "notes": poly.notes
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": polygon_coords
                    }
                })
            return jsonify({"type": "FeatureCollection", "features": features})
        print('--'*20)

    print('--'*20)
    print('this 3')
    print('--'*20)
    # If no completed result, load polygons from file
    # Compute path to project root (one level above 'app/')
    print('no completed result, load polygons from file')
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    json_path = os.path.join(project_root, 'results', 'polygons_02.json')
    print('json path:')
    print(json_path)
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            polygons_json = json.load(f)
        polygons_json.get("features", []).extend(features)
        return jsonify(polygons_json)

    return jsonify({"type": "FeatureCollection", "features": features})


def calculate_polygon_centroid(coordinates):
    """Calculate centroid of polygon coordinates"""
    if not coordinates:
        return [0, 0]

    x_sum = sum(coord[0] for coord in coordinates)
    y_sum = sum(coord[1] for coord in coordinates)
    count = len(coordinates)
    return [x_sum / count, y_sum / count]


def calculate_bounds(coordinates):
    """Calculate bounding box for all coordinates"""
    if not coordinates:
        return None

    lons = [coord[0] for coord in coordinates]
    lats = [coord[1] for coord in coordinates]

    return {
        "southwest": [min(lons), min(lats)],
        "northeast": [max(lons), max(lats)]
    }
