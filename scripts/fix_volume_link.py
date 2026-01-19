import os
import sys
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def move_volume(volume_id, new_storyline_id):
    print(f"--- Moving Volume {volume_id} to Storyline {new_storyline_id} ---")
    try:
        res = supabase.table("StoryVolumes").update({"storyline_id": new_storyline_id}).eq("id", volume_id).execute()
        if res.data:
            print("Success! Volume moved.")
            print(f"New Data: {res.data[0]}")
        else:
            print("Failed to update volume.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Move Volume d6970db6... to Storyline 87c35557... (The one in Ardent Knight 7)
    move_volume("d6970db6-c42c-4f09-9647-774e3f24256f", "87c35557-9668-4c1a-a0cb-5479cda52c78")