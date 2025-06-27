# src/gemma_analyzer.py
import requests
import json
import base64
from PIL import Image
import io

class DisasterAnalyzer:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        
    def analyze_damage(self, image_path, context=""):
        """Analyze disaster damage using Gemma 3n"""
        
        # Prepare image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        prompt = f"""
        Analyze this post-disaster UAV image for damage assessment:
        
        Context: {context}
        
        Please identify and classify:
        1. Building damage levels (no damage, minor, major, total destruction)
        2. Road conditions (clear, blocked)
        3. Debris presence and location
        4. Water/flooding areas
        5. Emergency access routes
        
        Provide response in JSON format with coordinates if visible landmarks exist.
        """
        
        payload = {
            "model": "gemma3n:2b",
            "prompt": prompt,
            "images": [image_data],
            "stream": False
        }
        
        response = requests.post(f"{self.ollama_url}/api/generate", 
                               json=payload)
        return response.json()