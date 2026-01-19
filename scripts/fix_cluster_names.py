import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_name(text):
    return text.replace('[', '').replace(']', '').replace('\n', '').strip()

def clean_cluster_names():
    print("--- Cleaning Cluster Names ---")
    
    # Fetch all seed atoms
    seed_res = supabase.table("Atoms").select("*").eq("type", "seed_prose").execute()
    
    if not seed_res.data:
        print("No seed atoms found.")
        return

    count = 0
    for atom in seed_res.data:
        meta = atom.get('metadata', {})
        raw_name = meta.get('cluster_name', '')
        
        # Use helper function
        cleaned = clean_name(raw_name)
        
        if cleaned != raw_name:
            print(f"Cleaning: '{raw_name}' -> '{cleaned}'")
            
            # Update Metadata
            meta['cluster_name'] = cleaned
            
            # Also update Atom Name if it contains the dirty string
            new_atom_name = atom['name'].replace(raw_name, cleaned)
            
            supabase.table("Atoms").update({
                "metadata": meta,
                "name": new_atom_name
            }).eq("id", atom['id']).execute()
            
            count += 1
            
    print(f"Cleaned {count} atoms.")

if __name__ == "__main__":
    clean_cluster_names()