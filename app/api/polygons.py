# app/api/polygons.py

from flask import Blueprint, jsonify
from sqlalchemy import select
from ..extensions import db
from ..models import AnalysisResult, PolygonFeature
import json

bp = Blueprint('polygons', __name__)
@bp.route('/api/polygons', methods=['GET'])
def get_polygons():
    results = db.session.scalars(select(AnalysisResult)).all()

    if not results:
        return jsonify({"type": "FeatureCollection", "features": []})

    features = []

    for result in results:
        # center point
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"center_{result}",
                "class": "center"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [result.center_lon, result.center_lat]
            }
        })

        # polygons
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
