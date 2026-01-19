import json
import logging
from db.session import get_db
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inspector")
load_dotenv()

def inspect_graph(volume_id):
    db = get_db()
    logger.info(f"Inspecting Graph for Volume: {volume_id}")

    try:
        response = db.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
        if not response.data:
            logger.error("Volume not found.")
            return

        graph = response.data.get('graph_structure', {})
        nodes = graph.get('nodes', [])
        connections = graph.get('connections', [])
        node_map = graph.get('node_id_map', {})
        master_asset_bank = graph.get('master_asset_bank')

        print(f"\n--- Graph Structure ---")
        print(f"Total Nodes: {len(nodes)}")
        print(f"Total Connections: {len(connections)}")
        print(f"Master Asset Bank Type: {type(master_asset_bank)}")
        if master_asset_bank:
            print(f"Master Asset Bank: {json.dumps(master_asset_bank, indent=2)}")
        
        print("\n--- Connections ---")
        for conn in connections:
            print(f"FROM: {conn.get('from')} -> TO: {conn.get('to')} ({conn.get('choice_label')})")

        print("\n--- Node Map ---")
        print(json.dumps(node_map, indent=2))

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    volume_id = "baf8c4a0-cb4e-425f-bdc3-98c23eb2157d"
    inspect_graph(volume_id)
