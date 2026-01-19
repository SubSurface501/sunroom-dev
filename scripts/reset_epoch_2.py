import os
import sys

# Inject project root into path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import get_db
from worker.src.agents.tasks import generate_manuscript

VOLUME_ID = "c3ca740b-6125-4187-a883-9413429d15c1"
USER_ID = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"

def reset_and_rerun():
    db = get_db()
    print(f"--- Resetting Nodes for Volume {VOLUME_ID} ---")
    
    # 1. Fetch current nodes to get content
    nodes = db.table("Nodes").select("id, content").eq("volume_id", VOLUME_ID).execute().data
    
    for node in nodes:
        content = node.get('content', {})
        # Reset fields
        content['pages'] = []
        content['production_status'] = 'pending'
        content.pop('ending_state', None)
        
        # Update
        db.table("Nodes").update({"content": content}).eq("id", node['id']).execute()
        print(f"Reset Node {node['id']}")

    # 2. Reset Volume Status
    db.table("StoryVolumes").update({"status": "drafting"}).eq("id", VOLUME_ID).execute()
    print("Volume status reset to 'drafting'.")

    # 3. Trigger Generation
    print("--- Triggering Manuscript Generation ---")
    generate_manuscript.delay(volume_id=VOLUME_ID, user_id=USER_ID)
    print("Task dispatched!")

if __name__ == "__main__":
    reset_and_rerun()
