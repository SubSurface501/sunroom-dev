import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Explicitly load the .env file
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment.")
    # Try to debug by printing what keys exist (masked)
    print(f"Available keys: {[k for k in os.environ.keys() if 'SUPABASE' in k]}")
    sys.exit(1)

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    sys.exit(1)

email = "jacob.ecommerce@gmail.com"
new_password = "tempPassword123!"

print(f"--- Manual Password Reset Tool ---")
print(f"Target: {email}")

try:
    # 1. Find User ID
    # The python library structure for admin might vary by version.
    # Trying standard approach.
    print("Searching for user...")
    
    # Note: list_users returns a UserList object in newer versions or a list.
    # We'll inspect what we get.
    response = supabase.auth.admin.list_users()
    
    # Check if response is a list or object with .users
    users_list = []
    if isinstance(response, list):
        users_list = response
    elif hasattr(response, 'users'):
        users_list = response.users
    else:
        print(f"Unexpected response format from list_users: {type(response)}")
        sys.exit(1)
        
    target_user = None
    for u in users_list:
        # User object usually has .email property
        if hasattr(u, 'email') and u.email == email:
            target_user = u
            break
    
    if not target_user:
        print(f"❌ User '{email}' not found in database.")
        sys.exit(1)
        
    print(f"✅ Found User ID: {target_user.id}")
    
    # 2. Update Password
    print(f"Updating password to '{new_password}'...")
    supabase.auth.admin.update_user_by_id(target_user.id, {"password": new_password})
    
    print(f"✅ Password updated successfully.")
    print(f"You can now log in with: {email} / {new_password}")

except Exception as e:
    print(f"❌ Error during operation: {e}")
    # Print full traceback for debugging
    import traceback
    traceback.print_exc()
