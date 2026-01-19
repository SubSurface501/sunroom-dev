import os

import logging
import vertexai
import google.auth

# Configure logging to see detailed output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_vertex_ai():
    """
    A minimal script to isolate and test Vertex AI initialization.
    """
    try:
        # Step 1: Log the environment variable to confirm it's being read
        impersonate_sa = os.environ.get("GOOGLE_IMPERSONATE_SERVICE_ACCOUNT")
        logging.info(f"Attempting to use service account for impersonation: {impersonate_sa}")
        if not impersonate_sa:
            logging.error("CRITICAL: GOOGLE_IMPERSONATE_SERVICE_ACCOUNT is not set!")
            return

        # Step 2: Explicitly get credentials
        logging.info("Attempting to get default Google Cloud credentials...")
        credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        logging.info(f"Successfully retrieved credentials for project: {project}")

        # Step 3: Initialize Vertex AI, with a timeout
        project_id = os.environ.get("GCP_PROJECT_ID", "thesunroom-476921")
        location = os.environ.get("GCP_LOCATION", "us-central1")
        
        logging.info(f"Attempting to initialize Vertex AI for project '{project_id}' in '{location}' with a 60-second timeout...")
        # NOTE: The 'init' function itself doesn't have a direct timeout argument.
        # The timeout will be enforced by the underlying gRPC channels configured by the env vars.
        vertexai.init(project=project_id, location=location, credentials=credentials)
        
        logging.info("SUCCESS: Vertex AI initialized successfully!")
        
        # Step 4: Try to load a model as a final confirmation
        logging.info("Attempting to load the Imagen 4 model...")
        from vertexai.preview.vision_models import ImageGenerationModel
        model = ImageGenerationModel.from_pretrained("imagen-4.0-generate-preview-06-06")
        logging.info(f"SUCCESS: Imagen 4 model loaded successfully: {model}")

    except Exception as e:
        logging.error(f"An error occurred during Vertex AI verification: {e}", exc_info=True)

if __name__ == "__main__":
    verify_vertex_ai()
