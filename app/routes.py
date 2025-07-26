import os
from flask import Blueprint, render_template, redirect, url_for, request, current_app, jsonify
from sqlalchemy import select
from werkzeug.utils import secure_filename
from .core.gemma_client import OllamaGemmaClient
from .models import AnalysisResult
from .tasks import analyze_image_task
from .extensions import db


main = Blueprint('main', __name__)

@main.route('/', methods=["POST", "GET"])
def index():
    if request.method == "POST":
        if 'images' not in request.files:
            return redirect(url_for('main.index'))
        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return redirect(url_for('main.index'))
        upload_path = current_app.config['UPLOAD_FOLDER']
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)

                # Trigger Celery task
                analyze_image_task.delay(file_path)

        return redirect(url_for('main.index'))

    return render_template("index.html")


# @main.route('/ask_gemma', methods=['POST'])
# def ask_gemma():
#     try:
#         # Fetch latest analysis result
#         latest_result = db.session.scalar(
#             select(AnalysisResult).order_by(AnalysisResult.created_at.desc())
#         )
#         if not latest_result:
#             return jsonify({"error": "No analysis results available"}), 404

#         image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], latest_result.image_filename)

#         # Get optional prompt from frontend
#         prompt = request.json.get("prompt", "Summarize the damage in this area.")

#         gemma_client = OllamaGemmaClient()
#         result = gemma_client.analyze_disaster_image(image_path, prompt_template="disaster_assessment")

#         return jsonify({"response": result})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
