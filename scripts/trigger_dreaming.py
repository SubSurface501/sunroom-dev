import os
import logging
import asyncio
import sys
from dotenv import load_dotenv

# Ensure we can import from project root
sys.path.append(os.getcwd())

# Load env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from worker.src.agents.distiller import DistillerAgent
from worker.src.agents.persona_builder import PersonaBuilderAgent
from db.session import get_db
from llm.client import get_llm_client

async def main():
    logger.info("✨ Starting MirrorMind Dreaming Cycle (Initialization)...")
    
    # Initialize Dependencies
    db = get_db()
    llm = get_llm_client()
    worker = None # We don't need the worker for direct execution here

    # 1. Distill Past Memories (The Long Night)
    # We'll run a 'yearly' distillation to catch up on everything
    logger.info("Phase 1: Distilling History...")
    try:
        distiller = DistillerAgent(db, worker, llm)
        
        # Fallback: Query atoms table to find distinct user_ids
        logger.info("Scanning for active users in Atoms table...")
        users_res = db.table("Atoms").select("user_id").limit(100).execute()
        
        if not users_res.data:
             logger.warning("No atoms found. System is tabula rasa.")
             user_ids = []
        else:
             user_ids = list(set([u['user_id'] for u in users_res.data]))
        
        logger.info(f"Found {len(user_ids)} active users to dream for.")
        
        for user_id in user_ids:
            logger.info(f"Processing User {user_id}...")
            # Distill (Yearly to catch all)
            distiller.run_task(user_id, time_window='yearly')
            
            # 2. Build Persona (Reflection)
            logger.info("Phase 2: Calibrating Persona...")
            persona_builder = PersonaBuilderAgent(db, worker, llm)
            persona_builder.run_task(user_id)

            # 3. Auto-Genesis (The Big Bang)
            logger.info("Phase 3: Auto-Genesis (Creating Lenses)...")
            from worker.src.agents.auto_genesis_agent import AutoGenesisAgent
            genesis = AutoGenesisAgent(db, worker, llm)
            genesis.run_task(user_id)
            
    except Exception as e:
        logger.error(f"Dreaming failed: {e}")

    logger.info("💤 Dreaming Complete. System is now Self-Aware.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())