import os
from flask import Flask
from .core.gemma_client import OllamaGemmaClient
# from .api.polygons import bp as polygons_bps
from .extensions import db, migrate, celery_init_app
from .models import *
from .routes import main as main_bp

gemma = OllamaGemmaClient()


def create_app():
    app = Flask(__name__,
            template_folder='web/templates',
            static_folder='web/static')

    app.config['UPLOAD_FOLDER'] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'data', 'input_images'))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['CELERY'] = {
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/0"
    }

    db.init_app(app)
    migrate.init_app(app, db)
    celery_init_app(app)

    # app.register_blueprint(polygons_bp)
    app.register_blueprint(main_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(fp):
            os.remove(fp)

    return app

app = create_app()
celery = app.extensions["celery"]

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
