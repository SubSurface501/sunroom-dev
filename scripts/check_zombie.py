import os
import sys
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def check_zombie_storyline(storyline_id):
    print(f"--- Checking Storyline {storyline_id} ---")
    try:
        res = supabase.table("Storylines").select("*").eq("id", storyline_id).single().execute()
        if res.data:
            sl = res.data
            print(f"ID: {sl['id']}")
            print(f"Name: {sl['name']}")
            print(f"Universe ID: {sl['universe_id']}")
            print(f"User ID: {sl['user_id']}")
        else:
            print("Storyline not found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_zombie_storyline("a00e3c8f-ccd8-44f0-9f7b-ec576217fe15")