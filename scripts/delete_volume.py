import os
import sys
import argparse
from supabase import create_client, Client

# Add project root to path to allow importing from db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.supabase_client import get_supabase_client

def delete_volume(db: Client, volume_id: str):
    """Deletes a volume and all its associated data."""
    try:
        print(f"--- Deleting data for volume: {volume_id} ---")

        # 1. Delete Trailheads
        trailhead_res = db.table("Trailheads").delete().eq("volume_id", volume_id).execute()
        print(f"Deleted {len(trailhead_res.data)} trailheads.")

        # 2. Delete Edges
        edge_res = db.table("Edges").delete().eq("volume_id", volume_id).execute()
        print(f"Deleted {len(edge_res.data)} edges.")

        # 3. Delete Nodes
        node_res = db.table("Nodes").delete().eq("volume_id", volume_id).execute()
        print(f"Deleted {len(node_res.data)} nodes.")
        
        # 4. Delete Branches
        branch_res = db.table("Branches").delete().eq("volume_id", volume_id).execute()
        print(f"Deleted {len(branch_res.data)} branches.")

        # 5. Delete StoryVolume
        vol_res = db.table("StoryVolumes").delete().eq("id", volume_id).execute()
        print(f"Deleted {len(vol_res.data)} story volume(s).")

        print(f"Successfully deleted volume {volume_id}.\n")

    except Exception as e:
        print(f"An error occurred while deleting volume {volume_id}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete one or all story volumes from the database.")
    parser.add_argument("volume_id", type=str, nargs='?', default=None, help="The ID of a specific volume to delete.")
    parser.add_argument("--all", action="store_true", help="Delete all volumes.")
    args = parser.parse_args()

    supabase_client = get_supabase_client()

    if args.all:
        if input("Are you sure you want to delete ALL volumes? This action cannot be undone. [y/N] ").lower() != 'y':
            print("Aborted.")
            sys.exit(0)
            
        print("Fetching all volume IDs...")
        try:
            response = supabase_client.table("StoryVolumes").select("id").execute()
            if response.data:
                volume_ids = [v['id'] for v in response.data]
                print(f"Found {len(volume_ids)} volumes to delete.")
                for volume_id in volume_ids:
                    delete_volume(supabase_client, volume_id)
                print("All volumes successfully deleted.")
            else:
                print("No volumes found to delete.")
        except Exception as e:
            print(f"An error occurred while fetching volumes: {e}")

    elif args.volume_id:
        delete_volume(supabase_client, args.volume_id)
        
    else:
        print("No action taken. Please provide a specific volume_id or use the --all flag.")
        parser.print_help()