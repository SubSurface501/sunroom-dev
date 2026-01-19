
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# IDs to unarchive
ids = [
    "c9cf551f-19ad-493a-9be9-c4d086d8b193", # Latest
    "748e9961-6b42-41f6-8d58-5fc5ba50602f"  # Time Thief
]

print(f"--- Unarchiving Volumes ---")

for vid in ids:
    # Check current status first
    vol = supabase.table("StoryVolumes").select("status, title").eq("id", vid).single().execute()
    if vol.data:
        print(f"\nVolume: {vol.data['title'][:30]}...")
        print(f"Current Status: {vol.data['status']}")
        
        # Reset to 'published' if it was finished, or 'draft' if not?
        # We don't know the state before archive. Safest is to check trailheads.
        # But for now, let's set to 'published' if it has content, or 'draft' if not.
        # Actually, let's just set to 'published' and if it fails, the user can click 'Greenlight' again?
        # No, Greenlight is for 'draft'.
        # Let's check if trailheads have content.
        
        head = supabase.table("Trailheads").select("content").eq("volume_id", vid).limit(1).execute()
        has_content = False
        if head.data and head.data[0]['content'].get('pages'):
            has_content = True
            
        new_status = 'published' if has_content else 'draft'
        
        supabase.table("StoryVolumes").update({"status": new_status}).eq("id", vid).execute()
        print(f"-> Restored to: {new_status}")
        
    else:
        print(f"Volume {vid} not found.")

