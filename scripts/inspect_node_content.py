import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

node_id = "427592a9-9297-40dc-90f2-c61ff4bb5c8c"
print(f"Checking Node: {node_id}")

node = supabase.table("Trailheads").select("content").eq("id", node_id).single().execute()
if node.data:
    content = node.data.get('content', {})
    print("Keys in content:", content.keys())
    if 'text' in content:
        print(f"Text length: {len(content['text'])}")
    if 'pages' in content:
        print(f"Pages count: {len(content['pages'])}")
        print(f"First page sample: {str(content['pages'][0])[:100]}")
else:
    print("Node not found.")
