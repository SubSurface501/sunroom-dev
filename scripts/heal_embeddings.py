import os
import sys
import logging
import json
import time

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import get_db
from llm.client import get_llm_client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def heal_embeddings():
    db = get_db()
    llm = get_llm_client()
    
    logger.info("--- Starting Embedding Healer ---")
    
    page_size = 50
    offset = 0
    total_repaired = 0
    
    while True:
        # Fetch atoms
        try:
            res = db.table("Atoms").select("id, name, content, embedding").range(offset, offset + page_size - 1).execute()
            atoms = res.data
        except Exception as e:
            logger.error(f"Failed to fetch atoms: {e}")
            break
            
        if not atoms:
            break
            
        logger.info(f"Checking batch {offset}-{offset+len(atoms)}...")
        
        batch_updates = 0
        
        for atom in atoms:
            emb = atom.get('embedding')
            needs_repair = False
            
            # Check for missing or zero-vector embeddings
            if not emb:
                needs_repair = True
            elif isinstance(emb, str):
                try:
                    emb_list = json.loads(emb)
                    if sum(abs(x) for x in emb_list) < 0.0001:
                        needs_repair = True
                except:
                    needs_repair = True
            elif isinstance(emb, list):
                if sum(abs(x) for x in emb) < 0.0001:
                    needs_repair = True

            if needs_repair:
                content = atom.get('content') or atom.get('name')
                if not content:
                    logger.warning(f"Skipping Atom {atom['id']} (No content)")
                    continue
                    
                logger.info(f"Repairing Atom {atom['id']} ({atom['name'][:30]})...")
                try:
                    # Generate new embedding using the fallback-enabled client
                    new_emb = llm.get_embedding(content)
                    
                    # Verify it's not zero
                    if sum(abs(x) for x in new_emb) > 0.0001:
                        db.table("Atoms").update({"embedding": new_emb}).eq("id", atom['id']).execute()
                        logger.info(f"-> Repaired.")
                        batch_updates += 1
                        total_repaired += 1
                        time.sleep(0.5) # Rate limit safety
                    else:
                        logger.error(f"-> Failed: Generated embedding was still zero.")
                except Exception as e:
                    logger.error(f"-> Failed: {e}")
        
        if batch_updates == 0:
            logger.info("Batch OK.")
            
        offset += page_size

    logger.info(f"--- Healer Complete. Repaired {total_repaired} atoms. ---")

if __name__ == "__main__":
    heal_embeddings()
