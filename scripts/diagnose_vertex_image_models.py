import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.cloud import aiplatform
import logging
import google.auth

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnose_vertex_image_models():
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GCP_LOCATION") or "us-central1"

    if not project_id:
        logger.error("GCP_PROJECT_ID environment variable is not set. Please set it in your .env file.")
        return

    try:
        logger.info(f"Initializing Vertex AI with Project: {project_id} in {location}")
        # Use Application Default Credentials (ADC)
        credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        vertexai.init(project=project_id, location=location, credentials=credentials)

        logger.info("\nAttempting to list available Image Generation Models...")
        # There isn't a direct genai.list_models() for Imagen.
        # We'll try to instantiate a few common names and see which one works.

        common_image_models = [
            "imagegeneration@006",
            "imagegeneration@latest",
            "imagegeneration-005", # This was the one that failed
            "imagen-4.0-generate-preview-06-06",
            "imagen-4.0-generate-001",
            "imagen-4.0-ultra-generate-001",
            "imagen-4.0-fast-generate-001"
        ]

        found_model = False
        for model_name in common_image_models:
            logger.info(f"Trying model: {model_name}")
            try:
                # Attempt to load the model. If it succeeds, it exists.
                _ = ImageGenerationModel.from_pretrained(model_name)
                logger.info(f"✓ Successfully found Image Generation Model: {model_name}")
                found_model = True
                break
            except Exception as e:
                logger.warning(f"✗ Model {model_name} not found or failed to load: {e}")
        
        if not found_model:
            logger.error("No common Image Generation Models were found. Please check Vertex AI documentation for available models in your region.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during Vertex AI Image Model diagnosis: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    diagnose_vertex_image_models()
