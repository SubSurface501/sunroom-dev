import os
import sys
import time
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env
load_dotenv()

# Import Agents directly (simulating the Celery tasks for this test script)
# In production, these would be Celery tasks.
from worker.src.agents.architect_v2 import VolumeArchitectAgent
from worker.src.agents.researcher import ResearcherAgent
from worker.src.agents.batch_producer import BatchProducerAgent
from db.session import get_db
from llm.client import get_llm_client
from celery import Celery

# Mock Worker for initialization
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
mock_worker = Celery('sunroom-worker', broker=broker_url)

def run_v3_test():
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    theme = "The History of the Golem"
    root_concept = "Golem"
    
    db = get_db()
    llm = get_llm_client()

    print(f"--- Starting V3 Pipeline Test: {theme} ---")

    # 1. The Architect (Map)
    print("\n[1/3] Running Volume Architect...")
    architect = VolumeArchitectAgent(db, mock_worker, llm)
    volume_id = architect.run_task(user_id, theme, root_concept)
    
    if not volume_id:
        print("Architect failed. Exiting.")
        return

    print(f"Volume Created: {volume_id}")
    time.sleep(2)

    # 2. The Researcher (Hydrate)
    print("\n[2/3] Running Researcher...")
    researcher = ResearcherAgent(db, mock_worker, llm)
    researcher.run_task(volume_id)
    print("Volume Hydrated.")
    time.sleep(2)

    # 3. The Builder (Build - Text Only)
    print("\n[3/3] Running Batch Producer (Text Only)...")
    producer = BatchProducerAgent(db, mock_worker, llm)
    producer.run_task(volume_id, mode="text_only", user_id=user_id)
    
    print("\n--- V3 Pipeline Test Complete ---")
    print(f"Check 'StoryVolumes' table for ID: {volume_id}")
    print(f"Check 'Trailheads' table for volume_id: {volume_id}")

if __name__ == "__main__":
    run_v3_test()
