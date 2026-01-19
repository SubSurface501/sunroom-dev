from db.session import get_db
from dotenv import load_dotenv

def clear_asset_bank(volume_id):
    load_dotenv()
    db = get_db()
    print(f"Clearing master_asset_bank for volume {volume_id}...")
    
    # Fetch current graph
    res = db.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
    graph = res.data.get('graph_structure', {})
    
    # Remove the key
    if 'master_asset_bank' in graph:
        del graph['master_asset_bank']
        
        # Update DB
        db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
        print("Cleared successfully.")
    else:
        print("Key not found, nothing to do.")

if __name__ == "__main__":
    volume_id = "baf8c4a0-cb4e-425f-bdc3-98c23eb2157d"
    clear_asset_bank(volume_id)
