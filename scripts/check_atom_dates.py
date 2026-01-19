import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_atom_dates():
    print("--- Inspecting Atom Dates ---")
    
    # 1. Fetch the 'Special Relativity' seed atom
    seed_res = supabase.table("Atoms").select("* ").eq("type", "seed_prose").execute()
    
    if not seed_res.data:
        print("No seed atoms found.")
        return

    print(f"Found {len(seed_res.data)} seed atoms.")
    
    for atom in seed_res.data:
        print(f"\nSeed Atom: {atom['name']}")
        print(f"  ID: {atom['id']}")
        print(f"  Created At Source: {atom.get('created_at_source')}")
        print(f"  Epoch Label: {atom.get('epoch_label')}")
        print(f"  Metadata: {atom.get('metadata')}")
        
        # 2. Check if any standard atoms exist that *should* be in this cluster
        # (Note: Standard atoms aren't explicitly linked to the cluster ID in the DB 
        # unless we tagged them, but we can check their general date status)
    
    print("\n--- Checking General Atom Date Distribution ---")
    # Check a sample of normal atoms
    atoms_res = supabase.table("Atoms").select("id, name, created_at_source").limit(10).neq("type", "seed_prose").execute()
    
    for atom in atoms_res.data:
        print(f"Atom: {atom['name'][:30]}... | Date: {atom.get('created_at_source')}")

if __name__ == "__main__":
    check_atom_dates()
