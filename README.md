# Gemma Disaster Assessment (Flask + Celery + Ollama)

A web-based application that allows uploading post-disaster UAV imagery, sends it to a Gemma model (via Ollama) for semantic analysis, and stores the structured polygon results in a database for later mapping and decision support.

---

## Requirements

- Python 3.10+
- Redis server running on `localhost:6379`
- Ollama running with `gemma3n` model installed
- PostgreSQL or SQLite (default: `sqlite:///site.db`)

---

## 🚀 Getting Started

### 1. Clone and set up your virtual environment

```bash
git clone https://github.com/your-username/gemma-disaster-assessment.git
cd gemma-disaster-assessment

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Database & Migrations

### 2. Initialize migrations

```bash
# Set Flask app entry
export FLASK_APP=manage.py

# Initialize migrations directory
flask db init

# Create initial migration
flask db migrate -m "Initial tables for analysis results"

# Apply migration
flask db upgrade
```

---

## Running the App

### 3. Start the Flask server

```bash
flask run --debug
```

Or with host exposed for testing on LAN:

```bash
flask run --debug --host=0.0.0.0
```

---

## Uploading & Processing

- Navigate to `/` and upload `.jpg`, `.png`, or `.jpeg` images.
- Images are saved to `data/input_images/`.
- Each upload triggers a background Celery task to analyze the image via Ollama API.
- The result polygons are saved to the database and can later be served or mapped.

---

## Running Celery

Make sure Redis is running first.

```bash
ExecStart=/path/to/venv/bin/celery -A celery_worker.celery worker --loglevel=info

celery -A app.extensions.celery worker --loglevel=info
```

---

## ⚙️ Ollama Setup

1. Install Ollama: https://ollama.com
2. Pull the required model:

```bash
ollama pull gemma3n
```

3. Ensure Ollama server is running on:
   `http://localhost:11434`

---

## 📂 Project Structure

```
app/
├── __init__.py
├── extensions.py
├── models.py
├── tasks.py
├── routes.py
├── core/
│   └── gemma_client.py
└── api/
    └── polygons.py
src/web/
├── templates/
│   └── index.html
├── static/
data/
└── input_images/
```

---

## ✅ Tips

- Modify `models.py` if you want to store more metadata or add user authentication.
- Use `flask shell` for DB inspection and testing.
- Use [Leaflet.js](https://leafletjs.com) in the frontend to render GeoJSON from your results.

---

## Reset DB (dev only)

```bash
flask db downgrade base
rm -rf migrations
flask db init
flask db migrate -m "reset"
flask db upgrade
```

---

## Author

Ilham Akbar
Contact or contribute via [GitHub](https://github.com/ilhamije) or [LinkedIn](https://linkedin.com/in/ilhamije).
