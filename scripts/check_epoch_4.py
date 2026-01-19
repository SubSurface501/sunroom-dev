import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Add project root to sys.path
sys.path.append(os.getcwd())

load_dotenv()

def check_epoch_4():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials not found.")
        return

    supabase = create_client(url, key)
    
    print("Checking for Epoch 4...")
    try:
        # Fetch Epoch 4
        res = supabase.table("Epochs").select("*").eq("id", 4).execute()
        if res.data:
            print(f"✅ Epoch 4 FOUND: {res.data[0]}")
        else:
            print("❌ Epoch 4 NOT FOUND.")
            
        # Fetch Active Epoch for the Universe (assuming one universe for now)
        uni_res = supabase.table("Universes").select("*").execute()
        for u in uni_res.data:
            print(f"Universe '{u['name']}' (ID: {u['id']}) Active Epoch: {u['active_epoch_id']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_epoch_4()
