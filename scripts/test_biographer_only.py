import os
import sys
import time
from dotenv import load_dotenv
from celery import Celery

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery('sunroom-worker', broker=broker_url, backend='rpc://', include=['worker.src.agents.tasks'])

def run_biographer_test(user_id: str, source_id: str):
    print(f"--- Triggering Biographer Agent for source {source_id} ---")
    celery_app.send_task('agents.biographer.run', kwargs={'user_id': user_id, 'source_id': source_id})
    print("Task sent. Monitor worker logs.")

if __name__ == "__main__":
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    source_id = "b75d0dfe-fc5a-42b0-be98-2780f9ed1c58" 
    run_biographer_test(user_id, source_id)