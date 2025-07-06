import requests
import base64
from pathlib import Path

class Gemma3nInference:
    def __init__(self, model_name='gemma3n:e4b-it', api_url='http://localhost:11434/api/generate'):
        self.model_name = model_name
        self.api_url = api_url

    def encode_image(self, image_path):
        """Encode image as base64 for Ollama API."""
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

    def run_inference(self, prompt, image_path=None):
        """
        Run inference using Ollama API.
        If image_path is provided, send as multimodal input.
        """
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        if image_path:
            data["images"] = [self.encode_image(image_path)]

        try:
            response = requests.post(self.api_url, json=data)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            return f"Error during inference: {e}"

# Example usage
if __name__ == '__main__':
    gemma = Gemma3nInference()
    prompt = "Describe the damage in this image for a SAR team."
    image_path = "data/sample_images/sample1.jpg"  # Replace with your image path
    output = gemma.run_inference(prompt, image_path)
    print(output)
