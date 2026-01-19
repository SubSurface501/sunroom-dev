
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

atom_id = "e8fe2678-0b31-461e-8f72-884438a59054"

response = supabase.from_("text_chunks").select("*").eq("atom_id", atom_id).execute()

if response.data:
    print(f"Text chunks found for Atom ID {atom_id}: {len(response.data)} chunks.")
    for chunk in response.data:
        print(f"  - Content: {chunk['content'][:50]}... (Embedding present: {chunk['embedding'] is not None})")
else:
    print(f"No text chunks found for Atom ID {atom_id}.")
