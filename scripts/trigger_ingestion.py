import os
import sys
from celery import Celery

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables (critical for Celery broker URL)
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '.env')))

# Configure Celery app (must match how it's defined in worker/src/agents/tasks.py)
broker_url = os.environ.get("CELERY_BROKER_URL", "pyamqp://guest@localhost//")
celery_app = Celery('sunroom-worker',
                     broker=broker_url,
                     backend='rpc://')

# User ID to trigger ingestion for
user_id = "5f24cb5b-8559-44e8-932d-0ce3c4c01bc1"

print(f"--- Sending ingestion task for user: {user_id} ---")

# Send the task
celery_app.send_task('agents.youtube_ingestion.run', kwargs={'user_id': user_id})

print("--- Ingestion task sent. Check Celery worker logs. ---")
