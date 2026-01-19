import os
import sys
from dotenv import load_dotenv
from celery import Celery

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0") # Use redis as broker
celery_app = Celery('sunroom-worker', broker=broker_url, backend='rpc://', include=['worker.src.agents.tasks'])

def trigger_agents(user_id: str, trailhead_id: str):
    print(f"Triggering Illustrator Agent for trailhead {trailhead_id}")
    celery_app.send_task('agents.illustrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})
    
    print(f"Triggering Narrator Agent for trailhead {trailhead_id}")
    celery_app.send_task('agents.narrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})

if __name__ == "__main__":
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # From test_agent.py
    trailhead_id = "8131ca68-7373-4ab7-9cdd-ebce0f8106cb" # From previous output
    
    trigger_agents(user_id, trailhead_id)
    print("Agent tasks sent to Celery. Check Celery worker logs for progress.")