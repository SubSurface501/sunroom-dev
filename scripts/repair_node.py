import logging
import sys
import os
from dotenv import load_dotenv
from db.session import get_db
from llm.client import get_llm_client
from worker.src.agents.storybook import StorybookAgent

# Load env
load_dotenv()

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_node():
    user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"
    node_id = "0efb404a-35ce-46a2-b1ee-c7ff3ca0fd12"
    vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
    
    logger.info(f"Reparing Node {node_id}...")
    
    db = get_db()
    llm = get_llm_client()
    
    # Get Assets from Volume
    vol = db.table("StoryVolumes").select("graph_structure").eq("id", vol_id).single().execute()
    assets = vol.data.get('graph_structure', {}).get('master_asset_bank', {})
    
    agent = StorybookAgent(db, None, llm) # None for worker since we aren't chaining
    
    # Run the task
    agent.run_task(user_id=user_id, trailhead_id=node_id, assets=assets)
    
    # Force update status
    node_res = db.table("Trailheads").select("content").eq("id", node_id).single().execute()
    if node_res.data:
        content = node_res.data.get('content', {})
        content['production_status'] = 'completed'
        db.table("Trailheads").update({"content": content}).eq("id", node_id).execute()
        logger.info("Node marked as completed.")

if __name__ == "__main__":
    repair_node()