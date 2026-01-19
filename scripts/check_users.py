import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("❌ Missing Supabase Admin keys.")
    exit(1)

supabase: Client = create_client(url, key)

print(f"🔍 Checking Auth Users for: {url}")

try:
    # List users (page 1)
    response = supabase.auth.admin.list_users()
    
    # Debug output to see what we got
    # print(f"DEBUG Response Type: {type(response)}")
    
    users = []
    if hasattr(response, 'users'):
        users = response.users
    elif isinstance(response, list):
        users = response
    # Handle the case where response might be a UserList object which behaves like a list but has no 'users' attr if it IS the list
    # In newer supabase-py versions, list_users returns a UserList object which contains the users.
    
    if not users and not isinstance(response, list) and not hasattr(response, 'users'):
         # Fallback for other response shapes
         print(f"⚠️ Unexpected response format: {response}")

    if not users:
        print("⚠️ No users found in Auth database.")
    else:
        print(f"✅ Found {len(users)} users:")
        for user in users:
            # user object might have different attributes depending on version
            email = getattr(user, 'email', 'No Email')
            uid = getattr(user, 'id', 'No ID')
            print(f" - {email} (ID: {uid})")
            
except Exception as e:
    print(f"❌ Error listing users: {e}")