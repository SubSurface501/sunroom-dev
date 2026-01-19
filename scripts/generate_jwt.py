import os
from supabase import create_client, Client

# Load Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_jwt():
    try:
        email = "testuser@example.com"
        password = "testpassword"

        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if response.session:
            session = response.session
            print(f"User {email} signed in successfully.")
            print(f"JWT: {session.access_token}")
            print(f"Refresh Token: {session.refresh_token}")
        else:
            print("Failed to sign in.")
            print(response)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_jwt()
