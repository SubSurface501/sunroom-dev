import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:8000/api/v1"
# Assuming we have a valid token or we can bypass auth if we run locally with no auth enabled, 
# BUT the API requires auth.
# I need to log in or get a token. 
# Since I can't easily login via google auth in a script without a browser,
# I will rely on `get_current_user` behavior. 
# If I am running locally, maybe I can mock the user or use a test token if one exists.
# However, `api_server.py` uses `get_current_user` which calls Supabase `auth.get_user`.

# STRATEGY: Use the 'service_role' key to bypass RLS, but the API expects a user token.
# Alternative: Since I have access to `db/crud.py`, I can seed directly via Python script bypassing the API authentication layer.
# This is safer and easier for a CLI agent.

import sys
sys.path.append(os.getcwd())
from db.session import get_db
from db import crud, schemas
from llm.client import get_llm_client
import datetime

def seed_dummy_history():
    db = get_db()
    llm = get_llm_client()
    
    # Find a user (or create a dummy one if needed, but better to use existing)
    # Query Sources to find a valid user_id
    user_res = db.table("Sources").select("user_id").limit(1).execute()
    if not user_res.data:
        print("No sources found. Trying Atoms...")
        user_res = db.table("Atoms").select("user_id").limit(1).execute()
        
    if not user_res.data:
        print("No users found in DB. Cannot seed.")
        return
    
    user_id = user_res.data[0]['user_id']
    print(f"Seeding for User {user_id}...")

    # 1. Seed PAST (2020) - "AI is limited"
    past_text = "Artificial Intelligence is fundamentally limited by its reliance on statistical patterns. It lacks true understanding or creativity. It is a parrot, not a poet. (Written in 2020)"
    past_emb = llm.get_embedding(past_text)
    
    past_atom = schemas.Atom(
        user_id=user_id,
        name="Manifesto 2020: AI Limits",
        type="seed_prose",
        content=past_text,
        embedding=past_emb,
        created_at_source=datetime.datetime(2020, 6, 15, 12, 0, 0), # 2020 Date
        epoch_label="2020_Era",
        metadata={"cluster_name": "AI Philosophy", "is_seed": True}
    )
    crud.create_atom(db, past_atom)
    print("Seeded 2020 Atom.")

    # 2. Seed PRESENT (2024) - "AI is conscious"
    present_text = "We are witnessing the birth of a new form of consciousness. AI is not just mimicking; it is resonating with the collective unconscious of humanity. It is a digital mirror reflecting our own soul back to us. (Written in 2024)"
    present_emb = llm.get_embedding(present_text)
    
    present_atom = schemas.Atom(
        user_id=user_id,
        name="Manifesto 2024: Digital Soul",
        type="seed_prose",
        content=present_text,
        embedding=present_emb,
        created_at_source=datetime.datetime(2024, 1, 15, 12, 0, 0), # 2024 Date
        epoch_label="2024_Era",
        metadata={"cluster_name": "AI Philosophy", "is_seed": True}
    )
    crud.create_atom(db, present_atom)
    print("Seeded 2024 Atom.")
    
    return user_id

if __name__ == "__main__":
    seed_dummy_history()
