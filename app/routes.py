import os
from flask import Blueprint, render_template, redirect, url_for, request, current_app, jsonify
from sqlalchemy import select
from werkzeug.utils import secure_filename
from .core.gemma_client import OllamaGemmaClient
from .models import AnalysisResult
from .tasks import analyze_image_task
from .extensions import db


main = Blueprint('main', __name__)

import uuid
from datetime import datetime

# Add to routes.py
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

                # Enhanced task with batch tracking
                analyze_image_task.delay(file_path, batch_id)
                processed_files.append(filename)

        # Store batch info in session or database
        results = jsonify({
            "status": f"upload {batch_id}",
            "files_count": len(processed_files),
            "files": processed_files
        })
        return render_template("index.html", results=results)

    return render_template("index.html", results=None)

# Add batch status endpoint
@main.route('/api/batch/<batch_id>/status', methods=['GET'])
def batch_status(batch_id):
    # Query database for batch completion status
    results = db.session.scalars(
        select(AnalysisResult).filter_by(batch_id=batch_id)
    ).all()

    return jsonify({
        "batch_id": batch_id,
        "total_expected": request.args.get('total', 0),
        "completed": len(results),
        "results": [{"id": r.id, "filename": r.image_filename} for r in results]
    })
