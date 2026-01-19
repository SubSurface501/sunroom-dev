import sys
import os
import logging
import time
import uuid
import json
from dotenv import load_dotenv

# Ensure we can import from worker
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# Setup logging to stream to console (stdout) only. File logging will be handled by PowerShell.
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear existing handlers to prevent duplicate output or conflicts
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 1. StreamHandler for console output (stdout)
import io # Import io for TextIOWrapper
console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

root_logger.addHandler(console_handler)

# For the script's specific logger
logger = logging.getLogger("full_saga_test")
logger.setLevel(logging.INFO) # Ensure this logger also processes INFO messages

from worker.src.agents.architect_v2 import VolumeArchitectAgent
from worker.src.agents.tasks import draft_volume_structure # Celery task wrapper
from db.session import get_db

def get_or_create_test_user(db_client):
    """Returns a hardcoded test user UUID to avoid email spam."""
    # HARDCODED TEST USER (To prevent Supabase Email Bounces)
    # Fixed ID retrieved from DB on 2026-01-05
    TEST_USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    logger.info(f"Using Hardcoded Test User ID: {TEST_USER_ID}")
    return TEST_USER_ID

def run_full_saga():
    logger.info("--- STARTING ARDENT KNIGHT FULL SAGA (V8) ---")
    
    db = get_db()
    
    # 1. Get or Create Test User to get a valid UUID
    try:
        user_id = get_or_create_test_user(db)
    except Exception as e:
        logger.error("Failed to get or create test user. Aborting saga.")
        return

    # 1. Create Universe & Storyline with valid UUIDs
    import uuid
    universe_id = str(uuid.uuid4())
    storyline_id = str(uuid.uuid4())
    
    logger.info(f"Using generated UUIDs -> Universe: {universe_id}, Storyline: {storyline_id}")
    
    # Clean previous run for this user to prevent "Zombie Data"
    try:
        logger.info(f"Cleaning up previous run data for user {user_id}...")
        # We need to fetch the volumes first to get their IDs for cascading deletes
        vol_res = db.table("StoryVolumes").select("id").eq("user_id", user_id).execute()
        if vol_res.data:
            volume_ids = [v['id'] for v in vol_res.data]
            if volume_ids:
                # Delete Edges and Nodes for those volumes
                db.table("Edges").delete().in_("volume_id", volume_ids).execute()
                db.table("Nodes").delete().in_("volume_id", volume_ids).execute()
                logger.info(f"Cleaned up child data for volumes: {volume_ids}")

        # Now delete the volumes themselves
        db.table("StoryVolumes").delete().eq("user_id", user_id).execute()
        logger.info("Cleanup complete.")
    except Exception as e:
        # Catch potential errors if RLS prevents direct deletion or other issues.
        logger.warning(f"Could not clean up previous run data for user {user_id}: {e}")

    
    # Create Universe if not exists
    # V8 UPDATE: Inject World Bible for Identity Consistency
    world_bible = {
        "entities": {
            "Anya": {
                "name": "Anya",
                "role": "The Ardent Knight",
                "is_protagonist": True,
                "pronouns": "She/Her", # Explicit Gender Anchor
                "description": "A determined knight in silver armor with a blue cape. She is practical, disciplined, and focused.",
                "forbidden_names": ["Kaelen", "Elara"],
                "traits": ["High Standing", "Knight of the Realm"],
                "aliases": ["The Ardent Knight", "Sir Knight", "She"]
            },
            "Thunder": {
                "name": "Thunder",
                "role": "Warhorse",
                "pronouns": "He/Him", # Explicit Gender Anchor
                "description": "A massive chestnut warhorse with a white blaze. Species: Equine. NOT a dog or wolf.",
                "forbidden_names": ["Shadow", "Roach"]
            }
        }
    }

    try:
        db.table("Universes").upsert({
            "id": universe_id, 
            "user_id": user_id, 
            "name": "Ardent Universe",
            "world_bible": world_bible
        }).execute()
    except Exception as e:
        logger.error(f"Failed to create or find Universe: {e}")
        # Decide if the script should stop if the universe can't be guaranteed
        return

    try:
        db.table("Storylines").upsert({"id": storyline_id, "universe_id": universe_id, "user_id": user_id, "name": "Main Quest"}).execute()
    except Exception as e:
        logger.error(f"Failed to create or find Storyline: {e}")
        # Decide if the script should stop
        return

    # --- SAGA PROSE ---
    epochs = [
        {
            "id": 1,
            "topic": "The Ardent Knight: Village Preparations",
            "seed": "The Ardent Knight is in the Town Hall of her quiet home village. She stands before a visiting Royal Advisor, who has traveled here specifically to command an official expedition into the landslide in the nearby hills. She accepts the order. She visits the local Blacksmith for rope and a cape. She visits the town archives to learn about the hills. She visits the Quartermaster for rations. She visits the Stablemaster for a horse. She sets off at the city gates saying goodbye to the locals."
        },
        {
            "id": 2,
            "topic": "The Ardent Knight: Forest Journey and Encounter",
            "seed": "[LAW: Latent Magic] She enters the forest after leaving the city gates. She notices the debris fields from the landslide. She continues into the hills. She begins to see a variety of small blue stones scattered across the forest floor. She keeps a few in her pocket for the Royal Advisor back in her village. Deep in the hills, the Ardent Knight is confronted by wolves, their eyes gleaming with unnatural hunger. She slays the wolves. She bandages her wounds. She arrives at the top of the trail."
        },
        {
            "id": 3,
            "topic": "The Ardent Knight: Ancient Ruin and Transformation",
            "seed": "[LAW: High Magic] The Ardent Knight discovers the origin of the landslide to be a large cavernous opening in the peaks. Inside the cavern, the Ardent Knight discovers an Ancient Ruin, humming with a low frequency. As she lowers herself down into the crevasse, the blue stones in her pocket begin to vibrate intensely. She navigates the dark crevasse, discovering a large door with blue sockets shaped like the stones she recovered earlier. When she places the stones in the sockets the door opens revealing chambers overflowing with forgotten treasures and powerful energy. She is changed by the power coursing through her."
        },
        {
            "id": 4,
            "topic": "The Ardent Knight: Return and Revelation",
            "seed": "She returns to the village gates, exhausted. The village locals notice the Ardent Knight is no longer the same. They see blue essence dripping from her when she walks by. Her final task is to stand before the Royal Advisor, present the strange blue stones, and deliver a report that will forever alter the kingdom's destiny."
        }
    ]

    from llm.client import LLMClient
    llm = LLMClient()
    architect = VolumeArchitectAgent(db, None, llm)
    from worker.src.agents.tasks import write_node_task
    from worker.src.agents.epoch_manager import EpochManagerAgent # V8.5 Fix

    all_volume_ids = []
    for i, epoch_data in enumerate(epochs):
        epoch_id = epoch_data['id']
        epoch_topic = epoch_data['topic']
        epoch_seed_prose = epoch_data['seed']

        logger.info(f"--- Processing Epoch {epoch_id}: {epoch_topic} ---")
        
        # 2. Draft Structure (Architect)
        logger.info(f"Drafting Volume for Epoch {epoch_id}...")
        
        volume_id = architect.run_task(
            user_id=user_id,
            topic=epoch_topic,
            depth=3, # Short for test
            seed_prose=epoch_seed_prose,
            universe_id=universe_id,
            storyline_id=storyline_id
        )
        
        if not volume_id:
            logger.error(f"Architect failed to return volume_id for Epoch {epoch_id}")
            continue # Use continue to allow subsequent epochs to run
        all_volume_ids.append(volume_id)

        logger.info(f"Volume {volume_id} Drafted. Launching Simulation & Writing for Epoch {epoch_id}...")
        
        # 3. Dispatch Writers (Simulation + Rendering)
        nodes = db.table("Nodes").select("id").eq("volume_id", volume_id).execute().data
        
        # V9 - Fetch initial world_bible
        world_bible_res = db.table("Universes").select("world_bible").eq("id", universe_id).single().execute().data
        current_world_bible = world_bible_res.get('world_bible', {})

        # V9 - Run sequentially to avoid race conditions on the world_bible
        for node in nodes:
            logger.info(f"Processing Node {node['id']} for Epoch {epoch_id}...")
            
            async_result = write_node_task.delay(node['id'], volume_id, current_world_bible)
            logger.info(f"  - Task for node {node['id']} dispatched. Waiting...")

            # THE HEARTBEAT:
            start_time = time.time()
            while not async_result.ready():
                # Print to terminal to prevent CLI tool timeout
                print(".", end="", flush=True)
                time.sleep(15) # Wait 15 seconds
                if time.time() - start_time > 600: # 10 minute total safety limit
                    logger.error("Task timed out after 10 minutes.")
                    break # Break out of the while loop

            # Check for failure before getting result
            if async_result.failed():
                logger.error(f"Task for node {node['id']} failed!")
                # Log the traceback from the worker
                logger.error(async_result.traceback)
                continue # Move to the next node
            
            # V13.2 - Handle NoneType Unpacking Error for timeouts
            if async_result.result is None:
                logger.error(f"Task for node {node['id']} returned NO RESULT (Timeout or other issue).")
                continue # Skip to next node in the for loop

            result, current_world_bible = async_result.result # Safely fetch the final result
            logger.info(f"  - Result for node {node['id']}: {result}")

        # V11.8 - Persist updated world_bible after each epoch
        try:
            db.table("Universes").update({"world_bible": current_world_bible}).eq("id", universe_id).execute()
            logger.info(f"Updated World Bible persisted for Universe {universe_id} after Epoch {epoch_id}.")
        except Exception as e:
            logger.error(f"Failed to persist updated World Bible for Universe {universe_id}: {e}")
            # Decide if the script should stop if persistence fails

        logger.info(f"--- WORLD BIBLE AFTER EPOCH {epoch_id} ---")
        logger.info(f"\n{json.dumps(current_world_bible, indent=2)}")
        logger.info(f"--- SAGA VOLUME FOR EPOCH {epoch_id} COMPLETE ---")

        # 4. V8.5 PERSISTENCE HANDOFF (The Epoch Gate)
        # We must manually trigger ledger inheritance so the NEXT epoch sees the items acquired in THIS epoch.
        if i < len(epochs) - 1:
            next_epoch_id = epochs[i+1]['id']
            logger.info(f"💾 Performing Cloud Save Handoff: Epoch {epoch_id} -> {next_epoch_id}...")
            
            # Update Universe Clock (So Architect sees the correct epoch)
            db.table("Universes").update({"active_epoch_id": next_epoch_id}).eq("id", universe_id).execute()
            
            # Inherit Ledger (Copy Inventory/State)
            # Note: We pass 'worker' as None because we are in a script, it might be unused or we mock it if needed.
            # EpochManagerAgent.__init__(self, db, worker, llm)
            epoch_manager = EpochManagerAgent(db, None, llm)
            epoch_manager.inherit_ledger(epoch_id, next_epoch_id)
            
            logger.info("✅ Handoff Complete. State Persisted.")



    logger.info("--- ALL SAGA VOLUMES COMPLETE ---")
    
    # 4. Verification (Verify the last volume generated)
    if all_volume_ids:
        last_volume_id = all_volume_ids[-1]
        logger.info(f"Performing verification on the last generated volume: {last_volume_id}")
        nodes_in_last_volume = db.table("Nodes").select("content").eq("volume_id", last_volume_id).limit(1).execute().data
        
        if nodes_in_last_volume:
            node = nodes_in_last_volume[0]
            content = node.get('content', {})
            
            if 'simulation_trace' in content:
                logger.info("✅ Simulation Trace found in Node Content for the last volume.")
            else:
                logger.error("❌ Simulation Trace MISSING for the last volume.")
                
            if content.get('pages') and any('narrative_text' in p for p in content['pages']):
                logger.info(f"✅ Narrative Text found in {len(content['pages'])} pages for the last volume.")
            else:
                logger.error("❌ Narrative Text MISSING for the last volume.")
        else:
            logger.error(f"❌ No nodes found for the last generated volume: {last_volume_id}.")
    else:
        logger.error("❌ No volumes were generated in the saga run.")

if __name__ == "__main__":
    run_full_saga()
