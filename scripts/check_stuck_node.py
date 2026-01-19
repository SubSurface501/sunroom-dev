import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
print(f"Checking 'Silence Falls' Node...")

nodes = supabase.table("Trailheads").select("id, content").eq("volume_id", vol_id).ilike("title", "%Silence Falls%").execute()

if nodes.data:
    node = nodes.data[0]
    content = node.get('content', {})
    print(f"ID: {node['id']}")
    print(f"Status: {content.get('production_status')}")
    if 'pages' in content:
        print(f"Pages count: {len(content['pages'])}")
    else:
        print("No pages found.")
else:
    print("Node not found.")
