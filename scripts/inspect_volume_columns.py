import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# Fetch one row to see keys
response = supabase.table("StoryVolumes").select("*").limit(1).execute()
if response.data:
    print("Columns found:", response.data[0].keys())
    
    # Specific Volume check
    vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
    vol = supabase.table("StoryVolumes").select("*").eq("id", vol_id).single().execute()
    if vol.data:
        print("\n--- Volume Data ---")
        print(f"ID: {vol.data.get('id')}")
        print(f"Outline: {str(vol.data.get('outline'))[:50]}...")
        print(f"Graph Structure: {str(vol.data.get('graph_structure'))[:50]}...")
else:
    print("No volumes found.")
