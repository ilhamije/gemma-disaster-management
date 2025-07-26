from flask import Blueprint, jsonify
from sqlalchemy import select
from ..extensions import db
from ..models import AnalysisResult, PolygonFeature
import json

bp = Blueprint('polygons', __name__)

@bp.route('/api/polygons', methods=['GET'])
def get_polygons():
    # Fetch latest N results, or all
    results = db.session.scalars(
        select(AnalysisResult).order_by(AnalysisResult.created_at.desc()).limit(10)
    ).all()

    all_features = []

    for result in results:
        # Add center point
        all_features.append({
            "type": "Feature",
            "properties": {
                "id": f"center_{result.id}",
                "class": "center",
                "color": "blue",
                "image": result.image_filename,
                "created_at": result.created_at.isoformat()
            },
            "geometry": {
                "type": "Point",
                "coordinates": [result.center_lon, result.center_lat]
            }
        })

        # Add associated polygons
        for poly in result.polygons:
            all_features.append({
                "type": "Feature",
                "properties": {
                    "id": poly.polygon_id,
                    "damage_type": poly.damage_type,
                    "confidence": poly.confidence,
                    "class": poly.class_label,
                    "notes": poly.notes,
                    "image": result.image_filename,
                    "result_id": result.id
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": json.loads(poly.coordinates)
                }
            })

    return jsonify({
        "type": "FeatureCollection",
        "features": all_features
    })
