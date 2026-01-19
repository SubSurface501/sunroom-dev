import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
from google.cloud.exceptions import NotFound
import google.auth
import google.genai as genai
from celery import Celery
import time
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.client import LLMClient # Used for getting embedding model details

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_supabase_admin() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
    return create_client(url, key)

def run_preflight_check(user_id: str, celery_app_path: str):
    """
    Performs a series of checks to validate external service connectivity and configuration.
    """
    print("\n--- Running Sunroom Pre-flight Check ---")
    all_passed = True

    # 1. Supabase Database Connection
    try:
        db = get_supabase_admin()
        db.from_('Universes').select('id').limit(1).execute() # Simple query to test connection
        logger.info("✓ Supabase Database Connection")
    except Exception as e:
        logger.error(f"✗ Supabase Database Connection: {e}")
        all_passed = False

    # 2. Supabase Storage Buckets
    try:
        db = get_supabase_admin() # Re-init in case of previous failure
        # Check for existence of buckets
        buckets_response = db.storage.list_buckets()
        bucket_names = [b.name for b in buckets_response]
        
        missing_buckets = []
        if 'storybook_images' not in bucket_names:
            missing_buckets.append('storybook_images')
        if 'storybook_pdfs' not in bucket_names:
            missing_buckets.append('storybook_pdfs')
        
        if missing_buckets:
            logger.error(f"✗ Supabase Storage Buckets: Missing {', '.join(missing_buckets)}. Please create them in your Supabase dashboard and ensure they are PUBLIC.")
            all_passed = False
        else:
            logger.info("✓ Supabase Storage Buckets (storybook_images, storybook_pdfs) Found.")
    except Exception as e:
        logger.error(f"✗ Supabase Storage Buckets: Failed to list buckets: {e}. Ensure Storage is enabled and service key has permissions.")
        all_passed = False

    # 3. Google Cloud Authentication
    try:
        _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        logger.info("✓ Google Cloud Authentication (Credentials available)")
    except google.auth.exceptions.RefreshError as e:
        logger.error(f"✗ Google Cloud Authentication: Reauthentication needed. Please run `gcloud auth application-default login`.")
        all_passed = False
    except Exception as e:
        logger.error(f"✗ Google Cloud Authentication: Failed to get credentials: {e}")
        all_passed = False

    # 4. Vertex AI Embedding Model Connectivity
    try:
        # Instantiate LLMClient in NON-DEBUG mode for actual connection test
        llm_client_real = LLMClient(debug_mode=False) 
        llm_client_real._ensure_vertex_initialized() # Call directly to initialize and check
        logger.info("✓ Vertex AI Embedding Model Connectivity")
    except ConnectionError as e:
        logger.error(f"✗ Vertex AI Embedding Model Connectivity: {e}. Check GCP_PROJECT_ID and `gcloud auth application-default login`.")
        all_passed = False
    except Exception as e:
        logger.error(f"✗ Vertex AI Embedding Model Connectivity: Failed to get embedding model: {e}")
        all_passed = False

    # 5. Celery Worker Status
    try:
        celery_app = Celery('worker.src.agents.tasks', broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        active_workers = celery_app.control.ping(timeout=1, destination=[])
        if active_workers:
            logger.info(f"✓ Celery Worker Status: Found {len(active_workers)} active worker(s).")
        else:
            logger.error("✗ Celery Worker Status: No active workers found. Please ensure your Celery worker is running.")
            all_passed = False
    except Exception as e:
        logger.error(f"✗ Celery Worker Status: Failed to ping workers: {e}. Ensure Celery broker is accessible and worker is running.")
        all_passed = False

    print("\n--- Pre-flight Check Complete ---")
    if all_passed:
        logger.info("✅ All critical checks passed. System is ready for generation.")
        return 0
    else:
        logger.error("❌ Some critical checks failed. Please review the errors above and fix them before proceeding.")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a pre-flight check for Sunroom system dependencies.")
    parser.add_argument("--user_id", type=str, default=os.environ.get("TEST_USER_ID", "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"), help="User ID to use for checks (e.g., storage access).")
    parser.add_argument("--celery_app_path", type=str, default="worker.src.agents.tasks", help="Path to the Celery app module.")
    
    args = parser.parse_args()
    
    # Load .env variables again explicitly if not already loaded by a preceding script
    load_dotenv() 

    sys.exit(run_preflight_check(args.user_id, args.celery_app_path))
