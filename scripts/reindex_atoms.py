import os
import time
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from llm.client import LLMClient

load_dotenv()

def reindex_atoms(limit_total=None):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Error: Missing Supabase credentials.")
        return

    supabase = create_client(url, key)
    llm = LLMClient()
    
    print("--- Starting Re-indexing of Atoms ---")
    
    total_processed = 0
    batch_size = 10
    
    while True:
        # Check explicit limit
        if limit_total and total_processed >= limit_total:
            print(f"Reached limit of {limit_total} atoms.")
            break

        # Fetch batch of atoms with no embedding
        # PostgREST syntax for "is null"
        response = supabase.table("Atoms").select("*").is_("embedding", "null").limit(batch_size).execute()
        atoms = response.data
        
        if not atoms:
            print("✅ All atoms have been indexed!")
            break
            
        print(f"\nFetching batch of {len(atoms)} atoms...")
        
        for atom in atoms:
            if limit_total and total_processed >= limit_total:
                break

            try:
                name = atom.get('name', 'Unknown')
                meta = atom.get('metadata') or {}
                description = meta.get('description', '')
                
                # Construct the semantic text
                text_to_embed = f"{name}: {description}".strip()
                
                if not text_to_embed:
                    print(f"Skipping {atom['id']} (No text content)")
                    continue

                print(f"[{total_processed + 1}] Embedding: {name[:30]}...")
                
                # Generate Vector
                vector = llm.get_embedding(text_to_embed)
                
                if not vector:
                    print(f"Failed to generate vector for {name}")
                    continue

                # Update DB
                supabase.table("Atoms").update({"embedding": vector}).eq("id", atom['id']).execute()
                total_processed += 1
                
                # Rate limit help
                time.sleep(0.2)
                
            except Exception as e:
                print(f"❌ Error processing atom {atom.get('id')}: {e}")
                time.sleep(1) # Backoff on error
        
        print(f"Batch complete. Total Processed so far: {total_processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill embeddings for Atoms.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of atoms to process (for testing).")
    args = parser.parse_args()
    
    reindex_atoms(limit_total=args.limit)
