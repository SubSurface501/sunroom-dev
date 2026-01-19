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

# Source IDs to re-trigger indexing for (from previous failed attempts)
source_ids = [
    "86ba7fd0-0616-4e4b-a547-c2913035c0be", # Reality Density Transfer
    "5646e6fc-c806-4e56-9cdc-7ea03ee77d00"  # Why we are here
]
user_id = "5f24cb5b-8559-44e8-932d-0ce3c4c01bc1"

print(f"--- Retrying IndexAtomAgent tasks for user: {user_id} ---")

for source_id in source_ids:
    print(f"--- Sending IndexAtomAgent task for source: {source_id} ---")
    celery_app.send_task('agents.indexing.run', args=[source_id, user_id])

print("--- Indexing retry tasks sent. Check Celery worker logs. ---")
