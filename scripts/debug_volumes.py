import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Add project root to sys.path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

supabase = create_client(url, key)

def list_recent_volumes():
    print("--- Fetching 5 Most Recent Volumes ---")
    try:
        res = supabase.table("StoryVolumes").select("id, title, status, universe_id, storyline_id, created_at").order("created_at", desc=True).limit(5).execute()
        
        for vol in res.data:
            print(f"ID: {vol['id']}")
            print(f"Title: {vol['title']}")
            print(f"Status: {vol['status']}")
            print(f"Universe ID: {vol['universe_id']}")
            print(f"Storyline ID: {vol['storyline_id']}")
            print(f"Created At: {vol['created_at']}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error fetching volumes: {e}")

if __name__ == "__main__":
    list_recent_volumes()