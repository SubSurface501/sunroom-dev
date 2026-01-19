from supabase import create_client, Client
import os

def get_db():
    """
    Returns a Supabase client instance for the worker (using service key).
    Reads environment variables just-in-time to ensure they are loaded.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment.")

    return create_client(supabase_url, supabase_service_key)
