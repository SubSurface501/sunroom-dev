import sys
import os
import time
import json
# Path hack to include project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import get_db
from llm.client import get_llm_client

def main():
    db = get_db()
    llm = get_llm_client()
    
    print("💧 Fetching atoms with NULL embeddings...")
    # Fetch atoms where embedding is null
    # Note: Supabase-py/Postgrest syntax for 'is null'
    response = db.table("Atoms").select("id, content, name").is_("embedding", "null").execute()
    atoms = response.data
    
    if not atoms:
        print("✅ No dry atoms found. All hydrated.")
        return

    print(f"Found {len(atoms)} dry atoms. Re-hydrating...")
    
    for i, atom in enumerate(atoms):
        try:
            content = atom.get('content') or atom.get('name', '')
            if not content: continue
            
            # Simple progress log
            print(f"[{i+1}/{len(atoms)}] Embedding: {atom['id']} ({content[:20]}...)")
            
            # Generate Embedding (768d from Gemini)
            vector = llm.get_embedding(content)
            
            # Update DB
            db.table("Atoms").update({"embedding": vector}).eq("id", atom['id']).execute()
            
            # Rate limit protection (Gemini free tier/standard tier has limits)
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"   ❌ Failed {atom['id']}: {e}")

    print("✅ Re-hydration complete.")

if __name__ == "__main__":
    main()
