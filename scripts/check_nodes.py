import os
import sys
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def check_nodes(volume_id):
    print(f"--- Checking Nodes for Volume {volume_id} ---")
    try:
        res = supabase.table("Nodes").select("*").eq("volume_id", volume_id).execute()
        print(f"Found {len(res.data)} nodes.")
        for n in res.data:
            print(f"- [{n['type']}] {n['title']}")
            
        # Check Graph Structure in Volume
        vol = supabase.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
        graph = vol.data.get('graph_structure', {})
        print(f"Graph Structure Keys: {graph.keys()}")
        if 'nodes' in graph:
            print(f"Graph JSON has {len(graph['nodes'])} nodes.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ID from previous step
    check_nodes("d6970db6-c42c-4f09-9647-774e3f24256f")