import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from the project root .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
TARGET_TITLE = "Saga: Mock Idea"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
    exit(1)

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def delete_duplicate_sagas():
    print(f"Searching for duplicates of '{TARGET_TITLE}' for user '{USER_ID}'...")
    
    # Get all entries for the specific title, ordered by creation date (newest first)
    response = client.table("Trailheads")\
        .select("id, created_at")\
        .eq("user_id", USER_ID)\
        .eq("title", TARGET_TITLE)\
        .order("created_at", desc=True)\
        .execute()
        
    data = response.data
    
    if not data or len(data) <= 1:
        print(f"No duplicates or only one instance of '{TARGET_TITLE}' found. No action needed.")
        return

    # The first item in the sorted list is the latest
    latest_id = data[0]['id']
    print(f"Found {len(data)} instances. Latest ID: {latest_id}")

    # Collect IDs of duplicates (all except the latest)
    duplicate_ids = [item['id'] for item in data[1:]]
    
    if duplicate_ids:
        print(f"Deleting {len(duplicate_ids)} duplicate(s)...")
        # Supabase doesn't have a direct 'delete where ID is in list'. We iterate.
        for dup_id in duplicate_ids:
            delete_response = client.table("Trailheads")\
                .delete()\
                .eq("id", dup_id)\
                .execute()
            if delete_response.data:
                print(f"Successfully deleted duplicate ID: {dup_id}")
            else:
                print(f"Failed to delete duplicate ID: {dup_id} - {delete_response.error}")
    else:
        print("No duplicates to delete.")

    print(f"Cleanup complete. Only the latest '{TARGET_TITLE}' (ID: {latest_id}) remains.")

if __name__ == "__main__":
    delete_duplicate_sagas()
