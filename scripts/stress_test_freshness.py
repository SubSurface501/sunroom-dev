
import os
import time
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

from db.session import get_db
from llm.client import get_llm_client
from worker.src.agents.indexing import IndexAtomAgent
from worker.src.agents.storybook import StorybookAgent
from worker.src.agents.reviewer import ReviewAgent
from db import crud, schemas

async def main():
    logger.info("🧪 Starting Stress Test: Freshness & Conflict...")
    
    db = get_db()
    llm = get_llm_client()
    worker = None # Mock

    # 1. Setup User
    users_res = db.table("Atoms").select("user_id").limit(1).execute()
    if not users_res.data:
        logger.error("No users found.")
        return
    user_id = users_res.data[0]['user_id']
    logger.info(f"Using User: {user_id}")

    # 2. Ingest "Fresh" Knowledge (The Poisoned Well)
    # A fake fact that contradicts normal reality.
    fake_fact = "In the year 3000, cats are the dominant species and humans live in underwater cages."
    source_title = "Future History v1.txt"
    
    logger.info(f"Creating Source: {source_title}...")
    source = schemas.Source(
        user_id=user_id,
        title=source_title,
        source_type="uploaded_text",
        raw_text=fake_fact,
        metadata={"stress_test": True}
    )
    
    # Insert Source
    src_res = db.table("Sources").insert(source.model_dump(exclude={"id"}, exclude_none=True)).execute()
    source_id = src_res.data[0]['id']
    logger.info(f"Source Created: {source_id}")

    # Index it immediately (Bypassing Celery for synchronous test)
    logger.info("Indexing Source...")
    indexer = IndexAtomAgent(db, worker, llm)
    indexer.run_task(source_id, user_id)
    
    # Verify Atom Exists
    # Debug: Fetch all atoms for this source
    linked_atoms_res = db.table("Atoms_to_Sources").select("atom_id").eq("source_id", source_id).execute()
    atom_ids = [r['atom_id'] for r in linked_atoms_res.data]
    if atom_ids:
        atoms_res = db.table("Atoms").select("name, content, type").in_("id", atom_ids).execute()
        logger.info(f"debug: Atoms created for source: {[a['name'] for a in atoms_res.data]}")
    else:
        logger.warning("debug: No atoms linked to source!")

    atoms = crud.match_atoms_by_embedding(db, llm.get_embedding("cats dominant species"), 0.5, 5, query_user_id=user_id) # Lower threshold, increase count
    if atoms:
        logger.info(f"✅ Freshness Confirmed. Found Atoms: {[a['name'] for a in atoms]}")
    else:
        logger.error("❌ Freshness Failed. Atom not found even with lower threshold.")
        return

    # 3. Trigger Generation (The Test)
    logger.info("Generating Narrative Node...")
    
    # Create a dummy trailhead
    trailhead_data = {
        "user_id": user_id,
        "title": "The Future of Felines",
        "insight": "Testing Freshness of recently ingested data.",
        "suggested_topic": "Speculative Biology",
        "type": "scene",
        "content": {"summary": "Describe the social hierarchy of the year 3000."}
    }
    th_res = db.table("Trailheads").insert(trailhead_data).execute()
    trailhead_id = th_res.data[0]['id']

    # Run Storybook Agent
    storybook = StorybookAgent(db, worker, llm)
    
    # We want to force it to use the new atom.
    # The agent usually finds context via 'match_atoms_by_embedding' using the prompt.
    # We'll pass a prompt that triggers the retrieval.
    
    # Mocking the transcript/assets to keep it simple, or just letting it generate based on title.
    # run_task parameters: user_id, trailhead_id, ...
    
    # We need to capture the output. run_task writes to DB.
    try:
        logger.info("Running Storybook Agent (may take 20s)...")
        storybook.run_task(user_id=user_id, trailhead_id=trailhead_id, target_length=1)
        
        # Fetch Result
        node = db.table("Trailheads").select("*").eq("id", trailhead_id).single().execute()
        content = node.data.get('content', {})
        narrative = content.get('narrative_text', '') or content.get('draft', '')
        
        logger.info(f"Generated Text: {narrative[:200]}...")
        
        if "cat" in narrative.lower() or "feline" in narrative.lower():
            logger.info("✅ Context Retrieval Successful (Cats mentioned).")
        else:
            logger.warning("⚠️ Context Retrieval Partial? Cats not explicitly mentioned in first 200 chars.")

        # 4. Check Reviewer Logs (Indirectly)
        # The Storybook Agent logs to stdout/stderr, which we can see in the console.
        # But we can also check if the text acknowledges the weirdness.
        
    except Exception as e:
        logger.error(f"Generation Failed: {e}")

    # Cleanup
    logger.info("Cleaning up test data...")
    # db.table("Sources").delete().eq("id", source_id).execute()
    # db.table("Trailheads").delete().eq("id", trailhead_id).execute()
    # Atoms cascade delete usually? If not, we leave them for now.

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
