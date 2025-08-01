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
        Ensures each feature has valid geometry following GeoJSON rules.
        Converts invalid Polygons or LineStrings into simpler types if needed.
        """
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])
        gtype = geom.get("type", "")

        # Polygon must have a closed ring with >= 4 points
        if gtype == "Polygon":
            if len(coords) == 1 and isinstance(coords[0], list):
                ring = coords[0]
                if len(ring) < 4:
                    if len(ring) == 1:
                        geom["type"] = "Point"
                        geom["coordinates"] = ring[0]
                    elif len(ring) == 2:
                        geom["type"] = "LineString"
                        geom["coordinates"] = ring
                    else:
                        geom["type"] = "Point"
                        geom["coordinates"] = ring[0]
                else:
                    # Ensure closed ring
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                    geom["coordinates"] = [ring]
            else:
                geom["type"] = "Point"
                geom["coordinates"] = coords[0] if coords else [0, 0]

        # LineString must have >= 2 coordinate pairs
        elif gtype == "LineString":
            if not isinstance(coords, list) or len(coords) < 2:
                geom["type"] = "Point"
                geom["coordinates"] = coords if isinstance(coords, list) else [0, 0]

        # Point must be a pair of numbers
        elif gtype == "Point":
            if not isinstance(coords, list) or len(coords) != 2:
                geom["coordinates"] = [0, 0]

        feature["geometry"] = geom
        return feature

    def _get_prompt_template(self, template_name: str) -> str:
        """
        Prompt template updated to explicitly request correct geometry type.
        """
        templates = {
            "disaster_assessment": """
Analyze this post-disaster UAV/aerial image for emergency response.

Identify and classify:
1. Building damage levels: no damage, minor damage, major damage, total destruction
2. Road conditions: clear, partially blocked, completely blocked
3. Debris presence and severity: none, light, moderate, heavy
4. Water/flooding: none, minor flooding, major flooding
5. Emergency access: accessible, limited access, no access
6. Visible hazards: electrical lines down, gas leaks, structural instability

Output structured JSON strictly following GeoJSON-like format.
- Use "Point" for single coordinate locations.
- Use "LineString" for linear features with two or more coordinates.
- Use "Polygon" ONLY if you provide a closed ring with at least four coordinate pairs (first == last).

Example output:
{
  "features": [
    {
      "properties": {
        "id": "building-1",
        "damage_type": "major damage",
        "class": "building_major_damage",
        "confidence": 0.92,
        "notes": "Roof partially collapsed"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-1234.567, 56.789],
            [-1233.456, 56.79],
            [-1233.45, 56.795],
            [-1234.56, 56.79],
            [-1234.567, 56.789]
          ]
        ]
      }
    },
    {
      "properties": {
        "id": "road-1",
        "damage_type": "partially blocked",
        "class": "road_partially_blocked",
        "confidence": 0.88,
        "notes": "Debris on road"
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-1235.0, 56.8],
          [-1235.5, 56.8]
        ]
      }
    }
  ]
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
