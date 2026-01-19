import sys
import os
import logging
import json
import uuid
from dotenv import load_dotenv

from dotenv import load_dotenv

load_dotenv() # Load other envs after setting the critical one

# Ensure we can import from worker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.client import LLMClient
from worker.src.agents.tasks import write_node_task
from db.session import get_db

# --- Logging Setup ---
# This setup streams all logs to the console with UTF-8 encoding.
import io
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
# --- End Logging Setup ---

from worker.src.agents.tasks import write_node_task
from db.session import get_db

def run_single_write():
    """
    Executes a single write_node_task synchronously for focused debugging.
    """
    logger = logging.getLogger("single_write_test")
    logger.info("--- STARTING SINGLE NODE WRITE TEST ---")
    
    db = get_db()
    llm = LLMClient()
    from worker.src.agents.architect_v2 import VolumeArchitectAgent

    try:
        # 1. Run Architect to generate a fresh volume and get live IDs
        logger.info("Running Architect to generate a new volume...")
        architect = VolumeArchitectAgent(db, None, llm)
        user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # Hardcoded test user
        
        # Minimal seed prose for a single-node test
        seed_prose = "Anya stands in the Town Hall, ready for her first task."
        
        # Create a temporary universe and storyline for this test
        universe_id = str(uuid.uuid4())
        storyline_id = str(uuid.uuid4())
        db.table("Universes").upsert({"id": universe_id, "user_id": user_id, "name": "Single Write Test Universe"}).execute()
        db.table("Storylines").upsert({"id": storyline_id, "universe_id": universe_id, "user_id": user_id, "name": "Single Write Test Storyline"}).execute()

        volume_id = architect.run_task(
            user_id=user_id,
            topic="Single Node Test",
            depth=1, # Only need a few nodes
            seed_prose=seed_prose,
            universe_id=universe_id,
            storyline_id=storyline_id
        )
        if not volume_id:
            logger.error("Architect failed to create a volume. Aborting.")
            return

        # 2. Fetch the new nodes and world bible
        nodes_res = db.table("Nodes").select("id").eq("volume_id", volume_id).limit(1).execute()
        if not nodes_res.data:
            logger.error("Architect ran but no nodes were created. Aborting.")
            return
            
        node_id = nodes_res.data[0]['id']
        logger.info(f"Generated Volume ID: {volume_id}")
        logger.info(f"Target Node ID for writing: {node_id}")

        uni_res = db.table("Universes").select("world_bible").eq("id", universe_id).single().execute()
        if not (uni_res.data and uni_res.data.get('world_bible')):
            logger.error("Could not fetch world_bible for the new universe.")
            return
            
        world_bible = uni_res.data.get('world_bible', {})
        logger.info("Successfully fetched World Bible for new universe.")

        # 3. Execute the task synchronously IN THIS PROCESS
        logger.info("Executing write_node_task.run() synchronously...")
        result, updated_world_bible = write_node_task.run(node_id, volume_id, world_bible)
        
        logger.info("--- SINGLE NODE WRITE TEST COMPLETE ---")
        logger.info(f"Result: {result}")
        logger.info("Final World Bible:")
        logger.info(json.dumps(updated_world_bible, indent=2))

    except Exception as e:
        logger.error("An error occurred during the single node write test.", exc_info=True)

if __name__ == "__main__":
    run_single_write()
