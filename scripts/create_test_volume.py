import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def get_supabase_admin() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    return create_client(url, key)

def create_test_volume(db: Client, user_id: str, topic: str):
    """
    Creates a new StoryVolume and a single root node for testing purposes.
    """
    print(f"Creating test volume with topic: '{topic}'")

    # 1. Create StoryVolume
    volume_data = {
        "user_id": user_id,
        "title": f"Test Volume: {topic}",
        "root_concept": topic,
        "status": "drafting",
        "graph_structure": {
            "style": "Cinematic, dark fantasy, hyper-realistic."
        }
    }
    res = db.table("StoryVolumes").insert(volume_data).execute()
    new_volume = res.data[0]
    volume_id = new_volume['id']
    print(f"Created StoryVolume with ID: {volume_id}")

    # 2. Create a Root Node
    node_id = str(uuid.uuid4())
    node_data = {
        "id": node_id,
        "volume_id": volume_id,
        "title": "The Beginning",
        "type": "root",
        "content": {
            "summary": "This is the summary of the root node for the test story about a knight searching for a lost artifact."
        }
    }
    db.table("Nodes").insert(node_data).execute()
    print(f"Created Root Node with ID: {node_id}")

    # 3. Update Volume's graph_structure with the root node ID
    graph = new_volume.get('graph_structure', {})
    graph['root_node_id'] = node_id
    graph['nodes'] = [{ "node_id": node_id, "type": "root" }]
    graph['connections'] = []
    db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
    print("Updated volume with root node information.")

    print(f"\nTest Volume ID: {volume_id}")
    return volume_id

if __name__ == "__main__":
    db = get_supabase_admin()
    user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"
    topic = "A test story about a knight searching for a lost artifact."
    
    import sys
    if len(sys.argv) > 1:
        topic = sys.argv[1]

    create_test_volume(db, user_id, topic)
