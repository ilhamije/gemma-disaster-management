# # src/core/tasks.py
# from celery import shared_task # Use shared_task for cleaner integration
# from .core.gemma_client import OllamaGemmaClient


# _gemma_client_for_tasks = OllamaGemmaClient()


# @shared_task(bind=True)
# def analyze_image_task(self, image_path: str):
#     """
#     Celery task to analyze an image using the OllamaGemmaClient.
#     """
#     self.update_state(state='PROGRESS', meta={'status': 'Starting image analysis...'})
#     print(f"Analyzing image: {image_path}") # For worker log

#     try:
#         result = _gemma_client_for_tasks.analyze_disaster_image(image_path)
#         print(f"Analysis complete for {image_path}: {result.get('status', 'No status')}")
#         self.update_state(state='PROGRESS', meta={'status': 'Analysis complete. Saving results...'})
#         return result
#     except Exception as e:
#         self.update_state(state='FAILURE', meta={'status': f"Analysis failed: {str(e)}"})
#         print(f"Analysis failed for {image_path}: {e}")
#         raise