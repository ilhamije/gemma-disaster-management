# src/core/gemma_client.py
import logging
import requests
import json
import base64
from pathlib import Path
import platform
# from ..config.ollama_config import OLLAMA_CONFIG
# from ..config import ollama_config


class GemmaClient:
    def __init__(self, config_path=None):
        if config_path is None:
            # Fix: Don't wrap strings in Path() when using / operator
            config_path = Path(__file__).parent.parent / \
                "config" / "ollama_config.json"
        else:
            print('Using custom config path:', config_path)

        self.config = self.load_config(config_path)
        self.base_url = self.config.get("base_url", "http://localhost:11434")
        self.model = self.config.get("model", "gemma3n:2b")
        self.timeout = self.config.get("timeout", 60)
        self.logger = logging.getLogger(__name__)

    def load_config(self, config_path):
        """Load platform-specific configuration"""
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Platform-specific adjustments
        system = platform.system()
        if system == "Darwin":  # macOS (M1)
            return config.get("macos", config.get("default", {}))
        else:  # Linux (Jetson)
            return config.get("linux", config.get("default", {}))

    def analyze_disaster_image(self, image_path, prompt_template="disaster_assessment"):
        """Analyze disaster imagery with Gemma 3n"""

        # Load image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        # Get prompt template
        prompt = self.get_prompt_template(prompt_template)

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
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}

    def get_prompt_template(self, template_name):
        """Get standardized prompts for different analysis types"""
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
                "damage_assessment": {
                    "buildings": {"no_damage": 0, "minor": 0, "major": 0, "destroyed": 0},
                    "roads": {"clear": 0, "blocked": 0, "impassable": 0},
                    "debris_level": "none|light|moderate|heavy",
                    "flooding": "none|minor|major",
                    "access_level": "full|limited|none",
                    "hazards": ["list of visible hazards"],
                    "priority_level": "low|medium|high|critical",
                    "response_recommendations": ["immediate actions needed"]
                },
                "confidence": 0.0-1.0,
                "analysis_notes": "detailed observations"
            }
            """,

            "rapid_triage": """
            Perform rapid damage triage for first responders:
            - Immediate threats to life safety
            - Infrastructure critical for rescue operations
            - Areas requiring immediate evacuation

            Respond with priority rankings and GPS coordinates if landmarks visible.
            """
        }
        return templates.get(template_name, templates["disaster_assessment"])
