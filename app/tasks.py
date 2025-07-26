import json
from celery import shared_task
from .core.gemma_client import OllamaGemmaClient
from .models import db, AnalysisResult, PolygonFeature
from pathlib import Path

@shared_task(bind=True)
def analyze_image_task(self, image_path: str):
    gemma_client = OllamaGemmaClient()
    self.update_state(state='PROGRESS', meta={'status': 'Starting image analysis...'})

    try:
        response = gemma_client.analyze_disaster_image(image_path)

        features = response.get("features", [])
        if not features:
            raise ValueError("No features found in response")

        # Estimate center for circle marker (average of all polygon first point lat/lon)
        lat_sum = 0
        lon_sum = 0
        count = 0

        polygons = []
        for feat in features:
            prop = feat["properties"]
            coords = feat["geometry"]["coordinates"]

            lon_sum += coords[0][0][0]
            lat_sum += coords[0][0][1]
            count += 1

            polygons.append(PolygonFeature(
                polygon_id=prop.get("id", ""),
                damage_type=prop.get("damage_type", ""),
                confidence=prop.get("confidence", 0.0),
                class_label=prop.get("class", ""),
                notes=prop.get("notes", ""),
                coordinates=json.dumps(coords)
            ))

        center_lat = lat_sum / count if count else 0.0
        center_lon = lon_sum / count if count else 0.0

        result = AnalysisResult(
            image_filename=Path(image_path).name,
            center_lat=center_lat,
            center_lon=center_lon,
            polygons=polygons
        )

        db.session.add(result)
        db.session.commit()

        return {"status": "completed", "result_id": result.id}
    except Exception as e:
        self.update_state(state='FAILURE', meta={'status': f"Analysis failed: {str(e)}"})
        raise
