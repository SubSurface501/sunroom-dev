import sys
import os
import logging
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker.src.agents.storybook import StorybookAgent
from db import crud, schemas
from db.session import get_db

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bridge_test():
    db = get_db()
    
    logger.info("🧪 --- STARTING MANUAL STYLE BRIDGE TEST ---")

    # 1. SETUP: Create Synthetic Data
    # Use existing user to satisfy FK constraint
    user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341" 
    logger.info(f"Using Test User ID: {user_id}")
    
    # Create Universe
    # CORRECTED: Passing user_id as separate arg
    uni = crud.create_universe(db, schemas.UniverseCreate(name="Bridge Test Universe"), user_id)
    logger.info(f"Created Universe: {uni.id}")

    # Define Styles
    style_epoch_1 = "Gritty, Industrial, Heavy. Focus on rust, ticking clocks, gear-oil, and the weight of machinery. The world feels inevitable and mechanical."
    style_epoch_2 = "Ethereal, Crystalline, Silent. Focus on light refraction, glass structures, weightlessness, and pure silence. The world feels hollow and fragile."

    # Create Epoch 1 (The Past)
    # CORRECTED: Passing user_id and universe_id as separate args
    ep1_data = schemas.EpochCreate(
        name="The Rust Age", 
        narrative_ledger={"inventory": ["Iron Key"]},
        seed_prose="The gears turned endlessly."
    )
    ep1 = crud.create_epoch(db, ep1_data, uni.id, user_id)
    
    # Manually update style
    db.table("Epochs").update({"style_summary": style_epoch_1}).eq("id", ep1.id).execute()
    logger.info(f"Created Epoch 1 (Rust): {ep1.id}")

    # Create Epoch 2 (The Present)
    ep2_data = schemas.EpochCreate(
        name="The Glass Age", 
        narrative_ledger={"inventory": ["Iron Key", "Glass Shard"]},
        seed_prose="The silence was deafening."
    )
    ep2 = crud.create_epoch(db, ep2_data, uni.id, user_id)
    db.table("Epochs").update({"style_summary": style_epoch_2}).eq("id", ep2.id).execute()
    
    # Set Active Epoch to 2
    db.table("Universes").update({"active_epoch_id": ep2.id}).eq("id", uni.id).execute()
    logger.info(f"Created Epoch 2 (Glass): {ep2.id} (ACTIVE)")

    # Create Volume in Epoch 2 (Direct Insert)
    vol_data = {
        "user_id": user_id,
        "universe_id": uni.id,
        "title": "Crossing the Threshold",
        "root_concept": "A traveler arrives in the new world.",
        "status": "drafting"
    }
    vol_res = db.table("StoryVolumes").insert(vol_data).execute()
    vol_id = vol_res.data[0]['id']
    logger.info(f"Created Volume: {vol_id}")

    # Create Branch (Required for Node)
    branch = crud.create_branch(db, schemas.BranchCreate(
        volume_id=vol_id,
        name="main",
        is_active=True
    ))
    logger.info(f"Created Branch: {branch.id}")

    # Create Node
    node_content = {
        "summary": "The traveler steps out of the Iron Gate and sees the Glass City for the first time. The transition is jarring.",
        "constraints": {"termination_condition": "Character takes first step onto glass."}
    }
    node = crud.create_node(db, schemas.NodeCreate(
        volume_id=vol_id, 
        branch_id=branch.id, 
        title="The Arrival", 
        type="narrative_beat", 
        content=node_content
    ))
    logger.info(f"Created Node: {node.id}")

    # Initialize Agent
    from llm.client import get_llm_client
    llm = get_llm_client()
    agent = StorybookAgent(db, None, llm)

    # --- TEST 1: CONTROL RUN (Native Epoch 2 Style) ---
    logger.info("\n🟢 TEST 1: CONTROL RUN (Using Native 'Glass Age' Style)")
    logger.info(f"Expected Voice: {style_epoch_2}")
    
    try:
        manifest_control = agent.run_task(
            user_id=user_id,
            node_id=node.id,
            volume_id=vol_id,
            universe_ids=[uni.id],
            target_length=1 # Short run
        )
        text_control = manifest_control['pages'][0]['narrative_text']
        logger.info(f"📝 RESULT (Control):\n{text_control}\n")
    except Exception as e:
        logger.error(f"Control run failed: {e}", exc_info=True)
        text_control = "FAILED"

    # --- TEST 2: BRIDGE RUN (Forced Epoch 1 Style) ---
    logger.info("\n🔴 TEST 2: BRIDGE RUN (Forcing 'Rust Age' Style into Glass Age Content)")
    logger.info(f"Expected Voice: {style_epoch_1}")
    
    # We patch the middleware method on the agent instance's middleware object
    # to return Style 1 instead of Style 2
    with patch.object(agent.energy_middleware, 'retrieve_epoch_style', return_value=(style_epoch_1, [])):
        try:
            manifest_bridge = agent.run_task(
                user_id=user_id,
                node_id=node.id, # Re-run on same node
                volume_id=vol_id,
                universe_ids=[uni.id],
                target_length=1
            )
            text_bridge = manifest_bridge['pages'][0]['narrative_text']
            logger.info(f"📝 RESULT (Bridge):\n{text_bridge}\n")
        except Exception as e:
            logger.error(f"Bridge run failed: {e}")
            text_bridge = "FAILED"

    # --- CLEANUP ---
    logger.info("Cleaning up test data...")
    # Delete universe (cascades)
    try:
        db.table("Universes").delete().eq("id", uni.id).execute()
        db.table("Atoms").delete().eq("user_id", user_id).execute()
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

    print("\n\n" + "="*60)
    print("COMPARISON REPORT")
    print("="*60)
    print(f"SCENE: {node_content['summary']}")
    print("-" * 60)
    print(f"STYLE 1 (Epoch 2 - Native): {style_epoch_2}")
    print(f"OUTPUT:\n{text_control}")
    print("-" * 60)
    print(f"STYLE 2 (Epoch 1 - Bridged): {style_epoch_1}")
    print(f"OUTPUT:\n{text_bridge}")
    print("="*60)

if __name__ == "__main__":
    run_bridge_test()