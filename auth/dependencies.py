
import os
from fastapi import Request, Depends, HTTPException
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase(request: Request) -> Client:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        # Allow anon for now if needed, or raise 401
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(
        headers={"Authorization": f"Bearer {token}"}
    ))

async def get_current_user(request: Request, supabase: Client = Depends(get_supabase)):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
             raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_response.user
    except Exception as e:
        print(f"Auth Error Type: {type(e)}")
        print(f"Auth Error Args: {e.args}")
        print(f"Token received: {token[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
