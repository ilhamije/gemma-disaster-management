# src/core/ollama_gemma_client.py
import requests
import base64
import logging
from pathlib import Path


class OllamaGemmaClient:

    def __init__(self):
        self.model = "gemma3n:e4b"
        self.ollama_url = "http://localhost:11434/api/generate"
        self.timeout = 180
        self.logger = logging.getLogger(__name__)


    def analyze_disaster_image(self, image_path: str, prompt_template: str = "disaster_assessment") -> dict:
        """
        Analyzes a disaster image using the Gemma model via Ollama's API.

        Args:
            image_path (str): The file path to the image to be analyzed.
            prompt_template (str, optional): The name of the prompt template to use.
                                             Defaults to "disaster_assessment".

        Returns:
            dict: The JSON response from the Ollama API, or an error dictionary.
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
            "images": [image_data],  # Ollama expects a list of base64 strings
            "stream": False,  # We want a single response, not a stream
            "options": {
                "temperature": 0.1,  # Lower temperature for more deterministic/factual responses
                "top_p": 0.9,        # Top-p sampling
                # Add other Gemma-specific or Ollama options
            }
        }

        response = requests.post(
            self.ollama_url,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        response_json = response.json()
        self.logger.info("Successfully received response from Ollama API.")
        return response_json

    def _get_prompt_template(self, template_name: str) -> str:
        """
        Retrieves a standardized prompt template by name.

        Args:
            template_name (str): The name of the desired prompt template.

        Returns:
            str: The prompt string, or an empty string if the template is not found.
        """
        # The prompt includes a JSON schema for the expected output,
        # guiding the model to produce structured results.
        templates = {
            "disaster_assessment": """
Analyze this post-disaster UAV/aerial image for emergency response:
Identify and classify:
1. Building damage levels: no damage, minor damage, major damage, total destruction
2. Road conditions: clear, partially blocked, completely blocked
3. Debris presence and severity: none, light, moderate, heavy
4. Water/flooding: none, minor flooding, major flooding
5. Emergency access: accessible, limited access, no access
6. Visible hazards: electrical lines down, gas leaks, structural instability

Provide response in structured JSON format:

{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "id": "<generated-damage-id>",
                "class": "<segmentation-class>",
                "confidence": <0.01 -- 0.99>,
                "notes": "<additional notes>"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [
                            xxx.xxxx,
                            yy.yyyy
                        ],
                        [
                            ...,
                            ...
                        ]
                    ]
                ]
            }
        },
        { ... }
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

    import json
    print(json.dumps(result, indent=2))
