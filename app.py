import os
from flask import request, redirect, url_for
from flask import Flask, render_template
from src.api.polygons import bp as polygons_bp
from werkzeug.utils import secure_filename


def create_app():
    app = Flask(__name__, template_folder='src/web/templates', static_folder='src/web/static')
    app.config['upload_folder']='input_images'
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


    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
