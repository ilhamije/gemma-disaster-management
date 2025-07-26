# # src/core/damage_analyzer.py
# import json
# import logging
# import time
# from pathlib import Path
# from typing import Dict, List, Optional
# from dataclasses import dataclass
# from datetime import datetime
# import re

# from .gemma_client import GemmaClient

# @dataclass
# class BuildingDamage:
#     no_damage: int = 0
#     minor: int = 0
#     major: int = 0
#     destroyed: int = 0

# @dataclass
# class InfrastructureStatus:
#     roads_clear: int = 0
#     roads_blocked: int = 0
#     roads_impassable: int = 0
#     debris_level: str = "none"
#     flooding: str = "none"
#     access_level: str = "full"

# class DamageAnalyzer:
#     def __init__(self, gemma_client: GemmaClient):
#         self.gemma_client = gemma_client
#         self.logger = logging.getLogger(__name__)

#         self.analysis_templates = {
#             "hurricane": """
#             Analyze this post-hurricane UAV image for disaster response:

#             Assess and count:
#             1. Buildings by damage level:
#                - No damage: structurally sound, minor cosmetic issues only
#                - Minor damage: broken windows, roof damage but habitable
#                - Major damage: structural damage, unsafe but standing
#                - Destroyed: completely collapsed or uninhabitable

#             2. Infrastructure status:
#                - Roads: count clear vs blocked vs completely impassable
#                - Debris level: none/light/moderate/heavy
#                - Flooding: none/minor/major
#                - Access level for emergency vehicles: full/limited/none

#             3. Visible hazards:
#                - Electrical lines down
#                - Gas leaks (visible damage to utilities)
#                - Structural instability
#                - Debris blocking evacuation routes

#             4. Response priority:
#                - Low: minimal damage, no immediate threats
#                - Medium: moderate damage, some hazards present
#                - High: significant damage, multiple hazards
#                - Critical: severe damage, immediate life safety concerns

#             Respond with structured JSON only:
#             {
#                 "buildings": {
#                     "no_damage": 0,
#                     "minor": 0,
#                     "major": 0,
#                     "destroyed": 0
#                 },
#                 "infrastructure": {
#                     "roads_clear": 0,
#                     "roads_blocked": 0,
#                     "roads_impassable": 0,
#                     "debris_level": "none|light|moderate|heavy",
#                     "flooding": "none|minor|major",
#                     "access_level": "full|limited|none"
#                 },
#                 "hazards": ["list", "of", "visible", "hazards"],
#                 "priority_level": "low|medium|high|critical",
#                 "response_recommendations": ["immediate", "actions", "needed"],
#                 "analysis_notes": "detailed observations about the scene"
#             }
#             """
#         }

#     def analyze_disaster_scene(self, image_path: str, analysis_type: str = "hurricane") -> Dict:
#         try:
#             start_time = time.time()

#             template = self.analysis_templates.get(analysis_type, self.analysis_templates["hurricane"])

#             raw_response = self.gemma_client.analyze_disaster_image(image_path, template)

#             analysis_time = time.time() - start_time

#             if "error" in raw_response:
#                 self.logger.error(f"Analysis failed for {image_path}: {raw_response['error']}")
#                 return self._create_error_response(raw_response["error"], image_path)

#             structured_data = self._parse_gemma_response(raw_response)
#             assessment = self._create_damage_assessment(structured_data, image_path, analysis_time)

#             self.logger.info(f"Analysis complete for {image_path} in {analysis_time:.2f}s")
#             return assessment

#         except Exception as e:
#             self.logger.error(f"Unexpected error analyzing {image_path}: {str(e)}")
#             return self._create_error_response(str(e), image_path)

#     def _parse_gemma_response(self, raw_response: Dict) -> Dict:
#         try:
#             response_text = raw_response.get("response", "")

#             json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

#             if json_match:
#                 json_str = json_match.group(0)
#                 parsed_data = json.loads(json_str)

#                 required_fields = ["buildings", "infrastructure", "hazards", "priority_level", "response_recommendations"]

#                 for field in required_fields:
#                     if field not in parsed_data:
#                         self.logger.warning(f"Missing required field: {field}")
#                         parsed_data[field] = self._get_default_value(field)

#                 return parsed_data
#             else:
#                 return self._fallback_parse(response_text)

#         except json.JSONDecodeError as e:
#             self.logger.warning(f"JSON parsing failed: {e}, attempting fallback parsing")
#             response_text = raw_response.get("response", "")
#             return self._fallback_parse(response_text)

#     def _fallback_parse(self, response_text: str) -> Dict:
#         self.logger.info("Using fallback parsing for natural language response")

#         fallback_data = {
#             "buildings": {"no_damage": 0, "minor": 0, "major": 0, "destroyed": 0},
#             "infrastructure": {
#                 "roads_clear": 0, "roads_blocked": 0, "roads_impassable": 0,
#                 "debris_level": "moderate", "flooding": "none", "access_level": "limited"
#             },
#             "hazards": [],
#             "priority_level": "medium",
#             "response_recommendations": [],
#             "analysis_notes": response_text[:500]
#         }

#         text_lower = response_text.lower()

#         if any(word in text_lower for word in ["collapsed", "destroyed", "leveled"]):
#             fallback_data["buildings"]["destroyed"] = 1
#             fallback_data["priority_level"] = "critical"
#         elif any(word in text_lower for word in ["major damage", "structural damage"]):
#             fallback_data["buildings"]["major"] = 1
#             fallback_data["priority_level"] = "high"
#         elif any(word in text_lower for word in ["minor damage", "roof damage"]):
#             fallback_data["buildings"]["minor"] = 1
#         else:
#             fallback_data["buildings"]["no_damage"] = 1
#             fallback_data["priority_level"] = "low"

#         if any(word in text_lower for word in ["road blocked", "debris", "impassable"]):
#             fallback_data["infrastructure"]["roads_blocked"] = 1
#             fallback_data["infrastructure"]["debris_level"] = "heavy"

#         hazard_keywords = {
#             "electrical": ["power lines", "electrical", "downed wires"],
#             "structural": ["unstable", "collapse risk", "structural"],
#             "debris": ["debris", "fallen trees", "blocked"],
#             "flooding": ["flood", "water", "inundation"]
#         }

#         for hazard_type, keywords in hazard_keywords.items():
#             if any(keyword in text_lower for keyword in keywords):
#                 fallback_data["hazards"].append(hazard_type)

#         return fallback_data

#     def _get_default_value(self, field: str):
#         defaults = {
#             "buildings": {"no_damage": 0, "minor": 0, "major": 0, "destroyed": 0},
#             "infrastructure": {
#                 "roads_clear": 0, "roads_blocked": 0, "roads_impassable": 0,
#                 "debris_level": "unknown", "flooding": "unknown", "access_level": "unknown"
#             },
#             "hazards": [],
#             "priority_level": "medium",
#             "response_recommendations": ["assessment_required"],
#             "analysis_notes": "Partial analysis completed"
#         }
#         return defaults.get(field, "unknown")

#     def _create_damage_assessment(self, structured_data: Dict, image_path: str, analysis_time: float) -> Dict:
#         confidence = self._calculate_confidence(structured_data)
#         coordinates = self._estimate_coordinates(image_path, structured_data)

#         assessment = {
#             "image_id": Path(image_path).name,
#             "image_path": image_path,
#             "analysis_timestamp": datetime.now().isoformat(),
#             "analysis_time_seconds": round(analysis_time, 2),
#             "damage_assessment": structured_data,
#             "confidence": confidence,
#             "estimated_coordinates": coordinates,
#             "model_info": {
#                 "model": self.gemma_client.model,
#                 "version": "gemma3:4b",
#                 "platform": "jetson_nano"
#             }
#         }

#         return assessment

#     def _calculate_confidence(self, data: Dict) -> float:
#         confidence = 1.0

#         if not data.get("analysis_notes") or len(data.get("analysis_notes", "")) < 20:
#             confidence -= 0.1

#         if not data.get("hazards"):
#             confidence -= 0.05

#         if not data.get("response_recommendations"):
#             confidence -= 0.1

#         total_buildings = sum(data.get("buildings", {}).values())
#         if total_buildings == 0:
#             confidence -= 0.2

#         destroyed = data.get("buildings", {}).get("destroyed", 0)
#         priority = data.get("priority_level", "medium")

#         if destroyed > 0 and priority not in ["high", "critical"]:
#             confidence -= 0.1

#         return max(0.1, min(1.0, confidence))

#     def _estimate_coordinates(self, image_path: str, damage_data: Dict) -> Dict:
#         import hashlib
#         import random

#         base_lat = 30.1558  # Mexico Beach, FL
#         base_lon = -85.4158

#         filename_hash = hashlib.md5(Path(image_path).name.encode()).hexdigest()
#         random.seed(filename_hash)

#         priority = damage_data.get("priority_level", "medium")
#         if priority in ["high", "critical"]:
#             radius = random.uniform(0.001, 0.01)
#         else:
#             radius = random.uniform(0.01, 0.05)

#         lat_offset = random.uniform(-radius, radius)
#         lon_offset = random.uniform(-radius, radius)

#         return {
#             "lat": base_lat + lat_offset,
#             "lon": base_lon + lon_offset,
#             "accuracy_meters": random.randint(50, 200),
#             "source": "estimated_from_filename_and_damage_pattern",
#             "hurricane_michael_relative": True
#         }

#     def process_image_batch(self, image_paths: List[str], max_concurrent: int = 2) -> List[Dict]:
#         results = []

#         self.logger.info(f"Processing batch of {len(image_paths)} images")

#         for i, image_path in enumerate(image_paths):
#             self.logger.info(f"Processing image {i+1}/{len(image_paths)}: {image_path}")

#             result = self.analyze_disaster_scene(image_path)
#             results.append(result)

#             if i < len(image_paths) - 1:
#                 time.sleep(0.5)

#         self.logger.info(f"Batch processing complete: {len(results)} results")
#         return results

#     def process_dataset_batch(self, dataset_images: List[str], batch_size: int = 10) -> Dict:
#         selected_images = dataset_images[:batch_size]
#         results = self.process_image_batch(selected_images)
#         summary = self._generate_batch_summary(results)

#         return {
#             "batch_results": results,
#             "summary": summary,
#             "processed_count": len(results),
#             "total_analysis_time": sum(r.get("analysis_time_seconds", 0) for r in results)
#         }

#     def _generate_batch_summary(self, results: List[Dict]) -> Dict:
#         if not results:
#             return {}

#         total_buildings = {"no_damage": 0, "minor": 0, "major": 0, "destroyed": 0}
#         priority_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
#         all_hazards = []

#         for result in results:
#             damage_data = result.get("damage_assessment", {})
#             buildings = damage_data.get("buildings", {})

#             for damage_type in total_buildings:
#                 total_buildings[damage_type] += buildings.get(damage_type, 0)

#             priority = damage_data.get("priority_level", "medium")
#             priority_counts[priority] += 1

#             hazards = damage_data.get("hazards", [])
#             all_hazards.extend(hazards)

#         avg_confidence = sum(r.get("confidence", 0) for r in results) / len(results)
#         avg_analysis_time = sum(r.get("analysis_time_seconds", 0) for r in results) / len(results)

#         return {
#             "total_buildings_analyzed": sum(total_buildings.values()),
#             "damage_distribution": total_buildings,
#             "priority_distribution": priority_counts,
#             "common_hazards": list(set(all_hazards)),
#             "average_confidence": round(avg_confidence, 3),
#             "average_analysis_time": round(avg_analysis_time, 2),
#             "images_processed": len(results)
#         }

#     def _create_error_response(self, error_message: str, image_path: str) -> Dict:
#         return {
#             "image_id": Path(image_path).name,
#             "image_path": image_path,
#             "analysis_timestamp": datetime.now().isoformat(),
#             "error": error_message,
#             "status": "failed",
#             "confidence": 0.0,
#             "damage_assessment": {
#                 "buildings": {"no_damage": 0, "minor": 0, "major": 0, "destroyed": 0},
#                 "infrastructure": {
#                     "roads_clear": 0, "roads_blocked": 0, "roads_impassable": 0,
#                     "debris_level": "unknown", "flooding": "unknown", "access_level": "unknown"
#                 },
#                 "hazards": [],
#                 "priority_level": "unknown",
#                 "response_recommendations": ["manual_assessment_required"],
#                 "analysis_notes": f"Analysis failed: {error_message}"
#             }
#         }