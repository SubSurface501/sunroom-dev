import os
from dotenv import load_dotenv
from supabase import create_client, Client

def delete_google_integration():
    """
    Deletes the Google integration for the test user to allow for a fresh
    OAuth flow and a new refresh token.
    """
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_service_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        return

    try:
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        # The user ID for our test user, testuser@example.com
        test_user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
        service_to_delete = "google"

        print(f"Attempting to delete integration for user '{test_user_id}' and service '{service_to_delete}'...")

        # Delete the specific row from the User_Integrations table
        response = supabase.table("User_Integrations").delete().eq("user_id", test_user_id).eq("service_name", service_to_delete).execute()

        print("Deletion response:", response)
        
        if response.data:
            print("Successfully deleted the old Google refresh token.")
        else:
            print("No token was found to delete, or an error occurred. Check the response above.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    delete_google_integration()
