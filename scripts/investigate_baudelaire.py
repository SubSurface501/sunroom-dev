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

def investigate_baudelaire():
    print("--- Investigating 'Charles Baudelaire' Source ---")
    
    # 1. Find the Atom
    atom_res = supabase.table("Atoms").select("*").ilike("name", "%Baudelaire%").execute()
    
    if not atom_res.data:
        print("No Baudelaire atoms found.")
        return

    for atom in atom_res.data:
        print(f"\nAtom: {atom['name']} (ID: {atom['id']})")
        meta = atom.get('metadata', {})
        source_id = meta.get('source_id')
        
        if source_id:
            print(f"  Linked Source ID: {source_id}")
            # 2. Fetch Source
            source_res = supabase.table("Sources").select("id, title, metadata, created_at").eq("id", source_id).single().execute()
            if source_res.data:
                s = source_res.data
                print(f"  Source Title: {s.get('title')}")
                print(f"  Source Metadata: {s.get('metadata')}")
                print(f"  Created At: {s.get('created_at')}")
            else:
                print("  Source record not found.")
        else:
            print("  No Source ID in atom metadata.")

if __name__ == "__main__":
    investigate_baudelaire()
