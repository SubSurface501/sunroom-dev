import os
import sys
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from db.session import get_db
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_embeddings():
    db = get_db()
    try:
        # Check total atoms
        res_total = db.table("Atoms").select("id, embedding", count="exact").execute()
        count = res_total.count
        logger.info(f"Total Atoms: {count}")
        
        if count == 0:
            return

        # Check for zero vectors (or effectively zero)
        # Since we can't easily query vector contents via standard PostgREST syntax for "all zeros",
        # we'll fetch a sample and check manually.
        res_sample = db.table("Atoms").select("id, name, embedding").limit(50).execute()
        
        zero_vector_count = 0
        valid_vector_count = 0
        
        for atom in res_sample.data:
            emb = atom.get('embedding')
            if not emb:
                logger.warning(f"Atom {atom['id']} ({atom['name']}) has NO embedding.")
                continue
                
            if isinstance(emb, str):
                emb = json.loads(emb)
            
            # Simple check: sum of absolute values
            magnitude = sum(abs(x) for x in emb)
            if magnitude < 0.0001:
                zero_vector_count += 1
                logger.warning(f"Atom {atom['id']} ({atom['name']}) has ZERO vector.")
            else:
                valid_vector_count += 1
        
        logger.info(f"Sample Check (50 atoms): {zero_vector_count} Zero Vectors, {valid_vector_count} Valid Vectors.")
        
    except Exception as e:
        logger.error(f"Error checking embeddings: {e}")

if __name__ == "__main__":
    check_embeddings()
