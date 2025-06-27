# src/damage_detector.py
import os
from pathlib import Path
import json


class DamageDetectionPipeline:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def process_rescuenet_dataset(self, dataset_path):
        """Process RescueNet images for damage assessment"""
        results = []

        image_dir = Path(dataset_path) / "images"

        for image_file in image_dir.glob("*.jpg"):
            try:
                # Analyze with Gemma 3n
                analysis = self.analyzer.analyze_damage(str(image_file))

                result = {
                    "image_path": str(image_file),
                    "timestamp": image_file.stat().st_mtime,
                    "analysis": analysis,
                    "damage_summary": self.extract_damage_summary(analysis)
                }

                results.append(result)
                print(f"Processed: {image_file.name}")

            except Exception as e:
                print(f"Error processing {image_file}: {e}")

        return results

    def extract_damage_summary(self, analysis):
        """Extract structured damage information"""
        # Parse Gemma 3n response and extract key damage indicators
        # This would depend on your specific prompt engineering
        pass
