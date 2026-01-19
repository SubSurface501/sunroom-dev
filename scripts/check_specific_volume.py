import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

vol_id = "f08c7390-87e7-4d62-b655-1ac258fe4bf8"
print(f"Checking Volume {vol_id} in DB...")

vol = supabase.table("StoryVolumes").select("title, theme, root_concept, graph_structure, status").eq("id", vol_id).single().execute()
if vol.data:
    print(f"Title: {vol.data.get('title')}")
    print(f"Theme: {vol.data.get('theme')}")
    print(f"Root Concept: {vol.data.get('root_concept')}")
    print(f"Status: {vol.data.get('status')}")
    graph = vol.data.get('graph_structure', {})
    if graph.get('nodes'):
        print(f"Root Node Summary: {graph['nodes'][0].get('summary')[:100]}...")
    else:
        print("No graph structure found.")
else:
    print("Volume not found in DB.")
