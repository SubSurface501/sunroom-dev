import os
import sys
import argparse
from supabase import create_client, Client
import json

# Add project root to path to allow importing from db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.supabase_client import get_supabase_client

def debug_volume(db: Client, volume_id: str):
    """Fetches volume data and node data to check for ID consistency."""
    try:
        print(f"--- Debugging Volume: {volume_id} ---")

        # 1. Fetch StoryVolume record
        print("\n1. Fetching StoryVolume record...")
        vol_res = db.table("StoryVolumes").select("id, graph_structure").eq("id", volume_id).single().execute()
        
        if not vol_res.data:
            print(f"❌ ERROR: No StoryVolume found with ID: {volume_id}")
            return

        volume_data = vol_res.data
        graph_structure = volume_data.get('graph_structure')

        if not graph_structure or 'nodes' not in graph_structure:
            print("❌ ERROR: The 'graph_structure' column is missing or does not contain 'nodes'.")
            print(f"   Raw graph_structure: {graph_structure}")
            return
            
        print("   ✅ Found StoryVolume record.")

        # 2. Find the root node ID from the graph_structure
        print("\n2. Finding root node ID in graph_structure...")
        graph_nodes = graph_structure.get('nodes', [])
        root_node_from_graph = next((n for n in graph_nodes if n.get('type') == 'root'), None)

        if not root_node_from_graph:
            print("❌ ERROR: Could not find a node with type 'root' in the graph_structure.")
            return

        root_id_from_graph = root_node_from_graph.get('node_id')
        if not root_id_from_graph:
            print("❌ ERROR: Root node in graph_structure is missing its 'node_id'.")
            return
            
        print(f"   ✅ Found root node ID in graph: {root_id_from_graph}")
        print(f"   (Is it a UUID? {'Yes' if len(root_id_from_graph) > 20 else 'No, this is likely the problem.'})")


        # 3. Fetch all Nodes from the Nodes table for this volume
        print("\n3. Fetching all associated records from 'Nodes' table...")
        nodes_res = db.table("Nodes").select("id, type, title").eq("volume_id", volume_id).execute()
        
        if not nodes_res.data:
            print(f"❌ ERROR: Found 0 nodes in the 'Nodes' table for volume_id {volume_id}.")
            return
            
        actual_nodes = nodes_res.data
        actual_node_ids = [node['id'] for node in actual_nodes]
        print(f"   ✅ Found {len(actual_nodes)} nodes in the 'Nodes' table.")
        print(f"   Actual Node IDs in DB: {json.dumps(actual_node_ids, indent=2)}")


        # 4. Compare the IDs
        print("\n4. Comparing graph root ID to actual node IDs...")
        
        if root_id_from_graph in actual_node_ids:
            print("   ✅ SUCCESS: The root node ID from the graph_structure exists in the Nodes table.")
        else:
            print("   ❌ FAILURE: The root node ID from graph_structure does NOT exist in the Nodes table.")
            print(f"      - Graph Root ID: {root_id_from_graph}")
            print("      - This ID needs to match one of the 'Actual Node IDs' listed above.")
            print("\n   ROOT CAUSE: This mismatch is why the story player cannot load the content.")
            print("   TO FIX: Please ensure the Celery worker process was restarted after the last code change and generate a new volume.")


    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug a story volume by checking for ID consistency between the volume's graph_structure and the Nodes table.")
    parser.add_argument("volume_id", type=str, help="The ID of the volume to debug.")
    args = parser.parse_args()

    supabase_client = get_supabase_client()

    if args.volume_id:
        debug_volume(supabase_client, args.volume_id)
    else:
        print("Please provide a volume_id.")
        parser.print_help()
