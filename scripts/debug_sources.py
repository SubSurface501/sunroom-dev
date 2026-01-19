import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

print("--- 📚 Library Inspection ---")
sources = supabase.table("Sources").select("id, raw_text, storage_path, metadata").execute()

for s in sources.data:
    text_len = len(s.get('raw_text') or "")
    path = s.get('storage_path')
    meta = s.get('metadata')
    print(f"ID: {s['id']}")
    print(f"  Path: {path}")
    print(f"  Text Len: {text_len}")
    print(f"  Meta: {meta}")
    print("-" * 20)