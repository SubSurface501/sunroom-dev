import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") # Admin Access

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def audit_leak():
    print("--- Forensic Audit: Data Ownership ---")
    
    # 1. Find the Baudelaire Source(s)
    print("Searching for Sources with 'Baudelaire' in title...")
    sources = supabase.table("Sources").select("id, user_id, title, created_at").ilike("title", "%Baudelaire%").execute()
    
    if not sources.data:
        print("No Baudelaire sources found.")
    else:
        for s in sources.data:
            print(f"Source: {s['title']}")
            print(f"  ID: {s['id']}")
            print(f"  Owner (User ID): {s['user_id']}")
            print(f"  Created: {s['created_at']}")
            
    # 2. Find the Special Relativity Source(s)
    print("\nSearching for Sources with 'Relativity' in title...")
    physics_sources = supabase.table("Sources").select("id, user_id, title, created_at").ilike("title", "%Relativity%").execute()
    
    if not physics_sources.data:
         print("No Relativity sources found.")
    else:
        for s in physics_sources.data:
            print(f"Source: {s['title']}")
            print(f"  ID: {s['id']}")
            print(f"  Owner (User ID): {s['user_id']}")
            print(f"  Created: {s['created_at']}")

    # 3. Compare User IDs
    print("\n--- Analysis ---")
    if sources.data and physics_sources.data:
        baudelaire_uid = sources.data[0]['user_id']
        physics_uid = physics_sources.data[0]['user_id']
        
        if baudelaire_uid == physics_uid:
            print(f"CRITICAL FINDING: Both sets of files are owned by the SAME User ID: {baudelaire_uid}")
            print("This implies the files were uploaded to the same account, or the user_id resolution is resolving both emails to the same UUID.")
        else:
            print(f"Files are owned by DIFFERENT User IDs.")
            print(f"  Baudelaire Owner: {baudelaire_uid}")
            print(f"  Physics Owner:    {physics_uid}")
            print("If you see Baudelaire clusters in the Physics account, the LEAK is in the Querying/Clustering logic.")

if __name__ == "__main__":
    audit_leak()
