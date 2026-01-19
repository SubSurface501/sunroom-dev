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

def run_v2_pipeline(user_id: str, trailhead_id: str, source_id_for_biographer: str):
    print(f"--- Starting V2 Pipeline for Trailhead {trailhead_id} ---")
    
    # 1. Re-run Biographer Agent (to generate new persona_v2.json and style_reference.txt)
    print(f"[1/2] Triggering Biographer Agent for source {source_id_for_biographer}...")
    celery_app.send_task('agents.biographer.run', kwargs={'user_id': user_id, 'source_id': source_id_for_biographer})
    
    print("Biographer Agent task sent. Waiting 1 minute for persona files to be generated...")
    time.sleep(60) # Give Biographer time to write files
    
    # 2. Trigger the full V2 Saga Pipeline (Storybook -> Director -> Illustrator -> Narrator -> Publisher)
    print(f"[2/2] Triggering Full Saga Pipeline V2 for trailhead {trailhead_id}...")
    celery_app.send_task('agents.pipeline.run_full_saga_v2', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})
    
    print("--- All V2 pipeline tasks dispatched. Monitor Celery worker logs and 'worker/output' for results. ---")

if __name__ == "__main__":
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" 
    trailhead_id = "8131ca68-7373-4ab7-9cdd-ebce0f8106cb" 
    # !!! IMPORTANT: Replace this with the actual Source ID of the Glitch Bottle transcript !!!
    source_id_for_biographer = "b75d0dfe-fc5a-42b0-be98-2780f9ed1c58" 
    
    run_v2_pipeline(user_id, trailhead_id, source_id_for_biographer)
