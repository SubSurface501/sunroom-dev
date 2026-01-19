import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Explicitly load .env from the project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env'))

_client: Client = None

def get_storage_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables.")
            
        _client = create_client(url, key)
    return _client

def upload_file(bucket_name: str, file_path: str, destination_path: str):
    """
    Uploads a file to a specified Supabase storage bucket.
    """
    client = get_storage_client()
    
    with open(file_path, 'rb') as f:
        response = client.storage.from_(bucket_name).upload(destination_path, f)
    
    if response.status_code != 200:
        # Check if the file already exists (409 Conflict)
        if response.status_code == 409 and 'duplicate key value violates unique constraint' in response.text:
             # If it already exists, just get the public URL
             pass
        else:
            raise Exception(f"Failed to upload file: {response.text}")
    
    return client.storage.from_(bucket_name).get_public_url(destination_path)