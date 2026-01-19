import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"

print(f"--- Debugging Atoms for User {user_id} ---")

# 1. Check Atom count
count = supabase.table("Atoms").select("id", count="exact").eq("user_id", user_id).execute()
print(f"Total Atoms: {count.count}")

# 2. Check Global Source Count (Is the DB empty?)
global_sources = supabase.table("Sources").select("id", count="exact").execute()
print(f"Global Sources in DB: {global_sources.count}")

# 3. Check Global Atom Count
global_atoms = supabase.table("Atoms").select("id", count="exact").execute()
print(f"Global Atoms in DB: {global_atoms.count}")
