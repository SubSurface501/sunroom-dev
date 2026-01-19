import os
import sys
import time
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env
load_dotenv()

# Import Agents directly (simulating the Celery tasks for this test script)
from worker.src.agents.batch_producer import BatchProducerAgent
from db.session import get_db
from llm.client import get_llm_client
from celery import Celery

# Mock Worker for initialization
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
mock_worker = Celery('sunroom-worker', broker=broker_url)

def run_v3_render_test():
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    # Use the Volume ID from the previous successful text run
    volume_id = "baf8c4a0-cb4e-425f-bdc3-98c23eb2157d"
    
    db = get_db()
    llm = get_llm_client()

    print(f"--- Starting V3 Full Render Test for Volume {volume_id} ---")

    # 3. The Builder (Build - Full Render)
    print("\n[3/3] Running Batch Producer (Full Render)...")
    print("This will trigger Casting -> Directing -> Illustrating -> Publishing.")
    
    producer = BatchProducerAgent(db, mock_worker, llm)
    producer.run_task(volume_id, mode="full_render", user_id=user_id)
    
    print("\n--- V3 Render Complete ---")
    print(f"Check 'worker/output/images/{volume_id}/' for output.")

if __name__ == "__main__":
    run_v3_render_test()
