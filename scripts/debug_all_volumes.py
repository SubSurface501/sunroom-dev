
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

print("--- ALL VOLUMES (Admin View) ---")
# Fetch ID, Title, User_ID, Status
vols = supabase.table("StoryVolumes").select("id, title, user_id, status, created_at").order("created_at", desc=True).limit(10).execute()

for v in vols.data:
    print(f"\nID: {v['id']}")
    print(f"Title: {v['title'][:50]}...")
    print(f"User: {v['user_id']}")
    print(f"Status: {v['status']}")
    print(f"Created: {v['created_at']}")

