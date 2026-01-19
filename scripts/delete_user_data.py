import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def get_supabase_admin() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
    return create_client(url, key)

def delete_all_data_for_user(email: str):
    """
    Deletes all data associated with a user's email address.
    This includes Atoms, Sources, StoryVolumes, Trailheads, and Series.
    """
    db = get_supabase_admin()

    print(f"--- Attempting to delete all data for: {email} ---")

    # 1. Get user_id from email
    try:
        res = db.rpc("get_user_id_by_email", {"user_email": email}).execute()
        user_id = res.data
        if not user_id:
            print(f"❌ ERROR: No user found with email '{email}'.")
            return
        print(f"✅ Found user ID: {user_id}")
    except Exception as e:
        print(f"❌ ERROR: Failed to get user ID. {e}")
        return

    # 2. CRITICAL: Confirm deletion
    confirm = input(f"🔴 WARNING: This will permanently delete all data (Atoms, Sources, Volumes, etc.) for this user.\nThis action is irreversible. Are you sure you want to continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return

    # 3. Proceed with deletion
    print(f"\n🔥 Deleting data for user {user_id}...")

    # The order is important to respect foreign key constraints.
    # Children must be deleted before parents.
    # Trailheads -> StoryVolumes
    # Atoms -> Sources
    # The order is important to respect foreign key constraints.
    # Children must be deleted before parents.
    # Trailheads -> StoryVolumes
    # Atoms -> Sources
    tables_to_delete = ["Atoms", "Trailheads", "Sources", "StoryVolumes", "Series"]
    
    for table_name in tables_to_delete:
        try:
            print(f"Deleting from {table_name}...")
            # Supabase Python client doesn't return count on delete, so we just execute
            db.table(table_name).delete().eq("user_id", user_id).execute()
            print(f"✅ Finished deleting from {table_name}.")
        except Exception as e:
            print(f"⚠️  Could not delete from {table_name}. Error: {e}")

    print("\n\n🎉 Data deletion process completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete all data for a specific user by email.")
    parser.add_argument("email", type=str, help="The email address of the user whose data should be deleted.")
    
    args = parser.parse_args()
    
    delete_all_data_for_user(args.email)
