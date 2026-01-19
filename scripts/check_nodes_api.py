import requests
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Direct DB check first to be 100% sure
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"

print("--- Checking DB directly ---")
nodes = supabase.table("Trailheads").select("id, content").eq("volume_id", vol_id).limit(1).execute()
if nodes.data:
    print("DB has content:", bool(nodes.data[0].get('content')))
    print("DB Content Keys:", nodes.data[0].get('content', {}).keys())
else:
    print("No nodes in DB")

# Now check API (simulating frontend)
# I need a token for this, but I can't easily generate one here. 
# I'll rely on the DB check since the API just wraps it.
