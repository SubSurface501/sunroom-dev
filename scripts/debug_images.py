
import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

volume_id = "0bb71d12-5bfe-4598-94a0-8d8025a6897b"

print(f"--- Inspecting Images for Volume: {volume_id} ---")

heads = supabase.table("Trailheads").select("id, title, content").eq("volume_id", volume_id).execute()

for h in heads.data:
    print(f"\nNode: {h['title']}")
    content = h.get('content', {})
    pages = content.get('pages', [])
    if not pages:
        print("  No pages found.")
        continue
        
    for p in pages:
        img_url = p.get('image_url')
        print(f"  Page {p.get('page_number')}: {img_url}")
        
        if img_url and os.path.exists(img_url):
            print("    [OK] File exists on disk.")
        elif img_url:
            print("    [MISSING] File NOT found on disk.")
