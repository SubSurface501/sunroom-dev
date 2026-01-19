import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Explicitly load .env from the project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env'))

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
        
    return create_client(url, key)
