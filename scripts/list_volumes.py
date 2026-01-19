
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

print("--- Listing Recent Volumes ---")
vols = supabase.table("StoryVolumes").select("id, title, created_at").order("created_at", desc=True).limit(5).execute()

for v in vols.data:
    print(f"\nID: {v['id']}")
    print(f"Created: {v['created_at']}")
    print(f"Title: {v['title']}")
    
    # Check first node for pages
    head = supabase.table("Trailheads").select("content").eq("volume_id", v['id']).limit(1).execute()
    if head.data:
        pages = head.data[0].get('content', {}).get('pages', [])
        print(f"Sample Node Page Count: {len(pages)}")
        if pages:
            print(f"Sample Image URL: {pages[0].get('image_url')}")
    else:
        print("No nodes found.")
