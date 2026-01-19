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

def trigger_regeneration(user_id: str, trailhead_id: str):
    print(f"--- Starting Regeneration for Trailhead {trailhead_id} ---")
    
    # 1. Trigger Illustrator (Visuals)
    print(f"[1/3] Triggering Illustrator Agent (Graphic Novel Style)...")
    celery_app.send_task('agents.illustrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})
    
    # 2. Trigger Narrator (Audio)
    print(f"[2/3] Triggering Narrator Agent (Voice: en-US-Journey-D)...")
    celery_app.send_task('agents.narrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})
    
    # 3. Trigger Publisher (PDF) - Delayed by 5 minutes to allow others to finish
    print(f"[3/3] Scheduling Publisher Agent (PDF Compilation) in 5 minutes...")
    celery_app.send_task('agents.publisher.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id}, countdown=300)
    
    print("--- All tasks dispatched. Monitor 'worker/output' for results. ---")

if __name__ == "__main__":
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # From test_agent.py
    trailhead_id = "8131ca68-7373-4ab7-9cdd-ebce0f8106cb" # Mock Idea
    
    trigger_regeneration(user_id, trailhead_id)