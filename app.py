import os
import requests
from flask import Flask, render_template
from flask import request, redirect, url_for, jsonify
from src.api.polygons import bp as polygons_bp
from werkzeug.utils import secure_filename


OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3n:e4b"


def create_app():
    app = Flask(__name__, template_folder='src/web/templates', static_folder='src/web/static')
    app.config['upload_folder']='data/input_images'
    app.register_blueprint(polygons_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload():
        if 'images' not in request.files:
            return redirect(url_for('index'))

        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return redirect(url_for('index'))

        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['upload_folder'], filename))
        return redirect(url_for('index'))

    @app.route('/ask_gemma', methods=['POST'])
    def ask_gemma():
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            return jsonify({"response": result.get("response", "")})
        except Exception as e:
            return jsonify({"error": str(e)}), 500



    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
