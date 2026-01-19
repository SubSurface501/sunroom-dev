import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import get_db
from db import crud, schemas
from worker.src.agents.tasks import draft_volume_structure

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_ID = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"
SEED_PROSE = """The Ardent Knight is in the Town Hall of her quiet home village. She stands before a visiting Royal Advisor, who has traveled here specifically to command an official expedition into the landslide in the nearby hills. She accepts the order. She visits the local Blacksmith for rope and a cape. She visits the town archives to learn about the hills. She visits the Quartermaster for rations. She visits the Stablemaster for a horse. She sets off at the city gates saying goodbye to the locals."""

def init_universe():
    db = get_db()
    
    # 1. Create Universe
    logger.info("creating Universe...")
    uni_create = schemas.UniverseCreate(
        name="The Ardent Knight's Journey",
        description=SEED_PROSE,
        archetype="MATERIALIST" # Start grounded
    )
    universe = crud.create_universe(db, uni_create, USER_ID)
    logger.info(f"Universe Created: {universe.id}")
    
    # 2. Create Epoch 1
    logger.info("Creating Epoch 1...")
    epoch_create = schemas.EpochCreate(
        name="Epoch 1: The Departure",
        seed_prose=SEED_PROSE,
        archetype="MATERIALIST"
    )
    epoch = crud.create_epoch(db, epoch_create, universe.id, USER_ID)
    logger.info(f"Epoch 1 Created: {epoch.id}")
    
    # 3. Activate Epoch
    logger.info("Activating Epoch...")
    crud.update_universe(db, universe.id, schemas.UniverseUpdate(active_epoch_id=epoch.id), USER_ID)
    
    # 4. Create StoryVolume
    logger.info("Creating StoryVolume...")
    vol_data = {
        "user_id": USER_ID,
        "title": "The Departure",
        "root_concept": SEED_PROSE,
        "status": "architecting",
        "universe_id": universe.id,
        "epoch_id": epoch.id,
        "is_epic": False
    }
    res = db.table("StoryVolumes").insert(vol_data).execute()
    volume = res.data[0]
    logger.info(f"Volume Created: {volume['id']}")
    
    # 5. Trigger Architect
    logger.info("Triggering Architect Task...")
    task = draft_volume_structure.delay(
        user_id=USER_ID,
        theme="The Departure",
        root_concept=SEED_PROSE,
        seed_prose=SEED_PROSE,
        volume_id=volume['id'],
        universe_id=universe.id,
        is_epic=False
    )
    logger.info(f"Task Dispatched: {task.id}")

if __name__ == "__main__":
    init_universe()