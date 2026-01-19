import json
import logging
from db.session import get_db
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inspector")
load_dotenv()

def inspect_ground_truth(node_id):
    db = get_db()
    logger.info(f"Inspecting Node: {node_id}")

    try:
        response = db.table("Trailheads").select("content").eq("id", node_id).single().execute()
        if not response.data:
            logger.error("Node not found.")
            return

        content = response.data.get('content', {})
        dossier = content.get('research_dossier', [])

        print(f"\n--- Research Dossier (Ground Truth) for Node {node_id} ---\n")
        if not dossier:
            print("No research dossier found.")
        else:
            for i, item in enumerate(dossier):
                print(f"Atom {i+1}: {item.get('name')}")
                print(f"   Definition: {item.get('definition')[:200]}...") # Truncate for readability
                print(f"   Source: {item.get('source', 'Unknown')}")
                print("-" * 40)

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    # Node: The Ritual Begins: The Four Elements
    node_id = "2df568b6-4c15-4a91-b38a-9e6c5e0f5ead"
    inspect_ground_truth(node_id)
