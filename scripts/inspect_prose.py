import os
import sys
import logging
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.session import get_db
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_node(node_id):
    db = get_db()
    try:
        # Fetch the specific node
        res = db.table("Nodes").select("*" ).eq("id", node_id).single().execute()
        if not res.data:
            logger.error(f"Node {node_id} not found.")
            return

        node = res.data
        content = node.get('content', {{}})
        pages = content.get('pages', [])
        
        print(f"--- Node {node_id} Analysis ---")
        print(f"Title: {content.get('title')}")
        print(f"Summary: {content.get('summary')}")
        print(f"Page Count: {len(pages)}")
        
        for i, page in enumerate(pages):
            print(f"\n--- Page {i+1} ---")
            narrative = page.get('narrative_text', '')
            print(f"Text ({len(narrative)} chars): {narrative[-200:]}") # Print last 200 chars to spot the ending
            
    except Exception as e:
        logger.error(f"Error inspecting node: {e}")

if __name__ == "__main__":
    # The ID in the URL likely corresponds to a Volume or a specific Node. 
    # Based on the URL structure /play/{id}, it's usually a Volume ID or a Node ID acting as a root.
    # Let's check if it's a volume first, if not found, assume it's a node.
    target_id = "71390e7c-fec6-4178-8e80-d368ee9e1ad9"
    
    db = get_db()
    
    # Check if Volume
    vol_res = db.table("StoryVolumes").select("id").eq("id", target_id).execute()
    if vol_res.data:
        print(f"ID matches a StoryVolume. Fetching all nodes for Volume {target_id}...")
        nodes_res = db.table("Nodes").select("id, content").eq("volume_id", target_id).order("created_at").execute()
        for n in nodes_res.data:
            inspect_node(n['id'])
    else:
        # Check if Node
        print(f"ID likely a Node. Checking...")
        inspect_node(target_id)
