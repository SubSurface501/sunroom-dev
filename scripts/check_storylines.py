import os
import sys
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def check_storylines(universe_id):
    print(f"--- Checking Storylines for Universe {universe_id} ---")
    try:
        res = supabase.table("Storylines").select("*").eq("universe_id", universe_id).execute()
        for sl in res.data:
            print(f"ID: {sl['id']} | Name: {sl['name']} | Created: {sl['created_at']}")
            
            # Check volumes count
            vols = supabase.table("StoryVolumes").select("id", "title").eq("storyline_id", sl['id']).execute()
            print(f"  -> Has {len(vols.data)} volumes.")
            if len(vols.data) > 0:
                print(f"     First Volume: {vols.data[0]['title'][:50]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_storylines("4ed40b4a-883a-4030-a639-26f721ef3ae0")