import os
import sys
from supabase import create_client

# Setup Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not set.")
    sys.exit(1)

supabase = create_client(url, key)

# Check all universes
try:
    res = supabase.table("Universes").select("*").execute()
    universes = res.data
    
    if not universes:
        print("No universes found.")
    else:
        print(f"Checking {len(universes)} universes for storylines...")
        for u in universes:
            # Check storylines
            s_res = supabase.table("Storylines").select("*").eq("universe_id", u['id']).execute()
            storylines = s_res.data
            
            if not storylines:
                print(f"  - [FIXING] Universe '{u['name']}' (ID: {u['id']}) has no storylines.")
                # Create one
                new_s = supabase.table("Storylines").insert({
                    "universe_id": u['id'],
                    "name": "Main Storyline",
                    "user_id": u['user_id']
                }).execute()
                print(f"    -> Created 'Main Storyline' (ID: {new_s.data[0]['id']})")
            else:
                # Optional: just print a dot or nothing to avoid spam
                # print(f"  - [OK] Universe '{u['name']}' has {len(storylines)} storyline(s).")
                pass
        print("Sync complete.")

except Exception as e:
    print(f"Error: {e}")
