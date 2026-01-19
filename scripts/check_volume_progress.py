import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
print(f"Checking Volume: {vol_id}")

# Check Volume Status
vol = supabase.table("StoryVolumes").select("status, manuscript").eq("id", vol_id).single().execute()
if vol.data:
    print(f"Status: {vol.data.get('status')}")
    ms = vol.data.get('manuscript')
    print(f"Manuscript Data Present: {bool(ms)}")
    if ms:
        print(f"Manuscript Keys: {list(ms.keys())}")
else:
    print("Volume not found.")

# Check Node Statuses
print("\nChecking Trailheads (Nodes)...")
nodes = supabase.table("Trailheads").select("id, content").eq("volume_id", vol_id).execute()
total = len(nodes.data)
completed = 0
pending = 0

for n in nodes.data:
    status = n.get('content', {}).get('production_status', 'pending')
    if status == 'completed':
        completed += 1
    else:
        pending += 1

print(f"Total Nodes: {total}")
print(f"Completed: {completed}")
print(f"Pending: {pending}")
