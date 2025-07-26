# celery_worker.py

from app import create_app
from app.extensions import celery_init_app

# Create Flask app instance
flask_app = create_app()

# Bind Celery with app context
celery = celery_init_app(flask_app)
