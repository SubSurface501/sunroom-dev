import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
print(f"Checking Nodes for Volume: {vol_id}")

nodes = supabase.table("Trailheads").select("id, title, content").eq("volume_id", vol_id).execute()

for n in nodes.data:
    status = n.get('content', {}).get('production_status', 'pending')
    print(f"Node: {n['title'][:30]}... - Status: {status}")

