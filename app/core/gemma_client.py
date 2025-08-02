# src/core/ollama_gemma_client.py
import requests
import base64
import logging
import json
from pathlib import Path

class OllamaGemmaClient:

    def __init__(self):
        self.model = "gemma3n:e4b"
        self.ollama_url = "http://localhost:11434/api/generate"
        self.timeout = 600  # Increased to 10 minutes
        self.logger = logging.getLogger(__name__)

    def analyze_disaster_image(self, image_path: str, prompt_template: str = "disaster_assessment") -> dict:
        """
        Analyzes a disaster image using the Gemma model via Ollama's API.

        Args:
            image_path (str): The file path to the image to be analyzed.
            prompt_template (str, optional): The name of the prompt template to use.

        Returns:
            dict: The JSON response from the Ollama API, with validated geometry.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            self.logger.error(f"Image file not found: {image_path}")
            return {"error": f"Image file not found: {image_path}", "status": "failed"}
        if not image_path.is_file():
            self.logger.error(f"Path is not a file: {image_path}")
            return {"error": f"Path is not a file: {image_path}", "status": "failed"}

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except IOError as e:
            self.logger.error(f"Error reading image file {image_path}: {e}")
            return {"error": f"Error reading image file: {e}", "status": "failed"}

        prompt = self._get_prompt_template(prompt_template)
        if not prompt:
            self.logger.error(f"Prompt template '{prompt_template}' not found.")
            return {"error": f"Prompt template '{prompt_template}' not found.", "status": "failed"}

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            response_json = response.json()

            if "response" in response_json:
                response_text = response_json["response"]
                # Attempt to extract JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    try:
                        parsed_json = json.loads(json_text)
                        # Validate geometries
                        parsed_json["features"] = [
                            self._validate_feature(f) for f in parsed_json.get("features", [])
                        ]
                        self.logger.info("Successfully received and validated response from Ollama API.")
                        return parsed_json
                    except json.JSONDecodeError:
                        self.logger.warning("Could not parse JSON from model response. Returning raw text.")

            self.logger.info("Successfully received response from Ollama API (no structured JSON parsed).")
            return response_json

        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timed out after {self.timeout} seconds")
            raise
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Ollama server")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise

    def _validate_feature(self, feature):
        """
        Validate and normalize a single GeoJSON feature from Gemma model output.
        Ensures polygons are wrapped and closed, and coordinates are valid.
        """
        if not feature or "geometry" not in feature or "type" not in feature["geometry"]:
            return None

        geom = feature["geometry"]
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])

        # Normalize Polygon structure
        if gtype == "Polygon":
            if coords and isinstance(coords[0][0], (int, float)):
                # Wrap if it's a flat list of points
                coords = [coords]
            # Ensure closure
            if coords and coords[0][0] != coords[0][-1]:
                coords[0].append(coords[0][0])
            geom["coordinates"] = coords

        elif gtype == "LineString":
            # Ensure it has at least 2 points
            if not isinstance(coords, list) or len(coords) < 2:
                return None

        elif gtype == "Point":
            # Ensure it's a valid coordinate pair
            if not isinstance(coords, list) or len(coords) != 2:
                return None

        # Default properties check
        if "properties" not in feature:
            feature["properties"] = {}

        return {
            "type": "Feature",
            "geometry": geom,
            "properties": feature["properties"]
        }


    def _get_prompt_template(self, template_name: str) -> str:
        """
        Prompt template improved for strict GeoJSON compliance and semantic clarity.
        """
        templates = {
            "disaster_assessment": """
    Analyze this UAV/aerial image of a post-disaster area for emergency response planning.

    Identify and classify visible features, choosing one of these categories:
    1. Buildings: building_no_damage, building_minor_damage, building_major_damage, building_total_destruction
    2. Roads: road_clear, road_partially_blocked, road_completely_blocked
    3. Debris: debris_light, debris_moderate, debris_heavy
    4. Water/Flooding: water_minor_flooding, water_major_flooding
    5. Access: access_limited, access_blocked
    6. Hazards: electrical_hazard, gas_leak, structural_instability

    **GeoJSON Output Requirements**:
    - Use geographic coordinates in EPSG:4326 (longitude, latitude).
    - Use `"Point"` for single coordinate features (e.g., hazard markers).
    - Use `"LineString"` for linear features (roads, barriers).
    - Use `"Polygon"` ONLY for areas and **ensure the outer ring is closed**
    (first coordinate pair == last coordinate pair, minimum 4 positions).
    - Avoid empty coordinates and invalid geometries.
    - Assign `properties.class` matching one of the allowed categories.
    - Include `properties.confidence` as a float (0–1) and short `properties.notes`.

    **Color legend (for client rendering):**
    const classColorMap = {
    "background": "#000000",
    "water": "#00BFFF",
    "building_no_damage": "#A0522D",
    "building_minor_damage": "#FFFF00",
    "building_major_damage": "#FFA500",
    "building_total_destruction": "#FF0000",
    "vehicle": "#FF00FF",
    "road_clear": "#808080",
    "road_partially_blocked": "#808000",
    "road_completely_blocked": "#804000",
    "tree": "#00FF00",
    "pool": "#0080FF",
    "center": "#3399FF"
    };

    **Strict output: return only valid JSON**
    (no extra text, no markdown, no explanations).

    ### Example output:
    {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "id": "debris-1",
                "damage_type": "light",
                "class": "debris_light",
                "confidence": 0.9,
                "notes": "Scattered debris on the ground.",
                "created_at": "2025-08-02T11:47:19.771498"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -85.43032979418332,
                            29.951160832214736
                        ],
                        [
                            -85.43032981489692,
                            29.9511608681092
                        ],
                        [
                            -85.43032985632412,
                            29.9511608681092
                        ],
                        [
                            -85.43032983561052,
                            29.95116085016197
                        ],
                        [
                            -85.43032979418332,
                            29.951160832214736
                        ]
                    ]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "id": "water-1",
                "damage_type": "minor flooding",
                "class": "water_minor_flooding",
                "confidence": 0.75,
                "notes": "Standing water near the building foundation.",
                "created_at": "2025-08-02T11:47:19.771606"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            -85.43032983561052,
                            29.95116085016197
                        ],
                        [
                            -85.43032985632412,
                            29.9511608681092
                        ],
                        [
                            -85.43032989775132,
                            29.95116088605643
                        ],
                        [
                            -85.43032987703772,
                            29.9511608681092
                        ],
                        [
                            -85.43032983561052,
                            29.95116085016197
                        ]
                    ]
                ]
            }
        }
    ],
    "properties": {
        "center_lat": 29.95190375,
        "center_lon": -85.42899502777777
    }
}
    """
        }
        return templates.get(template_name, templates["disaster_assessment"])



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Ollama Gemma Client")
    parser.add_argument("image_path", help="Path to the disaster image file (e.g. test.jpg)")
    args = parser.parse_args()

    client = OllamaGemmaClient()
    result = client.analyze_disaster_image(args.image_path)
    print(json.dumps(result, indent=2))
