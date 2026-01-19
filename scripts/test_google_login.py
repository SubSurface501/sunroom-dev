import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def run_test():
    """
    Automates the process of getting a JWT and initiating the Google login flow.
    """
    try:
        # --- 1. Get Supabase Credentials ---
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            print("❌ ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env file.")
            return

        # --- 2. Sign in to get a fresh JWT ---
        print("supabase: Signing in to get a fresh JWT...")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        email = "testuser@example.com"
        password = "testpassword"
        
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        if not response.session or not response.session.access_token:
            print("❌ ERROR: Failed to sign in to Supabase. Check credentials and user status.")
            print(response)
            return
            
        jwt_token = response.session.access_token
        print("✅ Success! Got JWT.")

        # --- 3. Make Authenticated Request to our API Server ---
        api_url = "http://localhost:8000/api/v1/auth/google/login"
        headers = {
            "Authorization": f"Bearer {jwt_token}"
        }
        
        print(f" server: Making request to {api_url}...")
        
        # Use a session object to persist cookies
        with requests.Session() as session:
            # IMPORTANT: allow_redirects=False is crucial. 
            # We don't want the script to follow the redirect, we want to capture the URL.
            api_response = session.get(api_url, headers=headers, allow_redirects=False)

            # --- 4. Process the Response ---
            if api_response.status_code == 307: # 307 is the Temporary Redirect status
                redirect_url = api_response.headers.get("Location")
                if redirect_url:
                    print("\n✅✅✅ SUCCESS! ✅✅✅")
                    print("\nCopy and paste this URL into your browser to continue:")
                    print("---------------------------------------------------------")
                    print(redirect_url)
                    print("---------------------------------------------------------")
                else:
                    print("❌ ERROR: Server responded with a redirect, but no 'Location' header was found.")
            else:
                print(f"❌ ERROR: Request to API server failed with status code {api_response.status_code}.")
                print("Response content:")
                print(api_response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: Could not connect to the API server at {api_url}.")
        print("Is the api_server.py running in another terminal?")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_test()