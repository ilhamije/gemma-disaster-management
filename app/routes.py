import os
import json
import uuid
from pathlib import Path

from flask import Blueprint, render_template, redirect, url_for, request, current_app, jsonify
from sqlalchemy import select
from werkzeug.utils import secure_filename

from .tasks import analyze_image_task
from .models import AnalysisResult, PolygonJSON
from .extensions import db

main = Blueprint('main', __name__)

# === Index & Upload ===
@main.route('/', methods=["POST", "GET"])
def index():
    if request.method == "POST":
        if 'images' not in request.files:
            return redirect(url_for('main.index'))

        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return redirect(url_for('main.index'))

        # Create batch session
        batch_id = str(uuid.uuid4())
        upload_path = current_app.config['UPLOAD_FOLDER']
        processed_files = []

        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)

                # Asynchronous analysis with batch tracking
                analyze_image_task.delay(file_path, batch_id)
                processed_files.append(filename)

        # Return immediate upload response
        return render_template("index.html", results={
            "status": f"upload {batch_id}",
            "files_count": len(processed_files),
            "files": processed_files
        })

    return render_template("index.html", results=None)


# === Batch Status ===
@main.route('/api/batch/<batch_id>/status', methods=['GET'])
def batch_status(batch_id):
    # Query database for analysis result entries
    results = db.session.scalars(
        select(AnalysisResult).filter_by(batch_id=batch_id)
    ).all()

    return jsonify({
        "batch_id": batch_id,
        "total_expected": request.args.get('total', 0),
        "completed": len(results),
        "results": [{"id": r.id, "filename": r.image_filename} for r in results]
    })


# === Polygons Endpoint ===
def feature_has_valid_coords(feature):
    try:
        coords = feature["geometry"]["coordinates"]
        for ring in coords:
            for lon, lat in ring:
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return False
        return True
    except Exception:
        return False

@main.route('/api/polygons', methods=['GET'])
def get_polygons():
    """
    Returns the latest combined polygons GeoJSON from PolygonJSON table.
    """
    polygon_json = db.session.scalar(select(PolygonJSON).order_by('created_at'))
    if polygon_json:
        try:
            geojson = json.loads(polygon_json.geojson)
            geojson["features"] = [f for f in geojson["features"] if feature_has_valid_coords(f)]
            return jsonify(geojson)
        except Exception as e:
            current_app.logger.error(f"Error parsing PolygonJSON: {e}")
            return jsonify({"type": "FeatureCollection", "features": []})

    # Fallback to static file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    json_path = os.path.join(project_root, 'results', 'polygons_02.json')
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            polygons_json = json.load(f)
        return jsonify(polygons_json)

    return jsonify({"type": "FeatureCollection", "features": []})
