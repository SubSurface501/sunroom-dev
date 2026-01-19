import os
import time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

print(f"Testing connection to: {url}")

try:
    start = time.time()
    print("Creating client...")
    supabase = create_client(url, key)
    print(f"Client created in {time.time() - start:.4f}s")

    print("Executing query...")
    start = time.time()
    # Set a timeout if possible, but supabase-py uses httpx which has defaults.
    # We'll just run a simple select.
    response = supabase.table("Sources").select("id").limit(1).execute()
    print(f"Query executed in {time.time() - start:.4f}s")
    print("Success!")
    print(response)

except Exception as e:
    print(f"FAILED: {e}")
