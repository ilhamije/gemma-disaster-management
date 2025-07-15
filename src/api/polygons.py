from flask import Blueprint, jsonify
import json

bp = Blueprint('polygons', __name__)

@bp.route('/api/polygons')
def get_polygons():
    # filename = 'results/polygons.json'
    filename = 'results/polygons_02.json'
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        # Return example static data if file not found
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": "damage_001",
                        "damage_type": "severe",
                        "confidence": 0.92,
                        "notes": "Collapsed building, route blocked"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [106.8025, -6.2015],
                                [106.8030, -6.2010],
                                [106.8035, -6.2015],
                                [106.8030, -6.2020],
                                [106.8025, -6.2015]
                            ]
                        ]
                    }
                }
            ]
        }
    return jsonify(data)
