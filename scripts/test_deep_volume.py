import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from worker.src.agents.architect_v2 import VolumeArchitectAgent
from db.session import get_db
from llm.client import get_llm_client
from celery import Celery

# Mock Worker
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
mock_worker = Celery('sunroom-worker', broker=broker_url)

def run_deep_test():
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    topic = "The Alchemist's Last Secret"
    depth = 6 # Deep Test with Bottlenecks
    
    db = get_db()
    llm = get_llm_client()

    print(f"--- Starting Deep Volume Test: {topic} (Depth {depth}) ---")

    architect = VolumeArchitectAgent(db, mock_worker, llm)
    volume_id = architect.run_task(user_id, topic, depth=depth)
    
    if volume_id:
        print(f"\nSUCCESS: Volume {volume_id} created.")
        print("Run 'test_v3_render.py' (modified) or manual steps to hydrate and render.")
    else:
        print("FAILED.")

if __name__ == "__main__":
    run_deep_test()