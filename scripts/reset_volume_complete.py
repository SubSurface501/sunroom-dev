import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import get_db
from worker.src.agents.tasks import generate_manuscript

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_ID = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"
VOL_ID = "8d8eff80-9a38-4bd8-9c3d-96f03cc08fe1"

def reset_and_run():
    db = get_db()
    
    logger.info(f"--- Resetting ALL Nodes for Volume {VOL_ID} ---")
    
    # Fetch all nodes
    nodes = db.table("Nodes").select("id, content").eq("volume_id", VOL_ID).execute().data
    
    for n in nodes:
        content = n.get('content', {})
        content['production_status'] = 'pending'
        # Wipe prose
        content.pop('pages', None)
        content.pop('ending_state', None)
        
        db.table("Nodes").update({"content": content}).eq("id", n['id']).execute()
        logger.info(f"Reset Node {n['id']}")

    # Reset Volume Status
    db.table("StoryVolumes").update({"status": "drafting"}).eq("id", VOL_ID).execute()
    logger.info("Volume status reset to 'drafting'.")

    # Trigger Generation
    logger.info("--- Triggering Manuscript Generation ---")
    task = generate_manuscript.delay(volume_id=VOL_ID, user_id=USER_ID)
    logger.info(f"Task dispatched: {task.id}")

if __name__ == "__main__":
    reset_and_run()