
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

print("--- Cleanup: Archiving Stuck Volumes ---")

# Fetch volumes that are stuck in progress
response = supabase.table("StoryVolumes").select("id, title, status").in_("status", ["rendering", "hydrated", "draft", "writing", "illustrating", "text_ready"]).execute()

if response.data:
    for vol in response.data:
        print(f"Archiving: {vol['title'][:30]}... (Status: {vol['status']})")
        supabase.table("StoryVolumes").update({"status": "archived"}).eq("id", vol['id']).execute()
    print("Cleanup complete.")
else:
    print("No stuck volumes found.")
