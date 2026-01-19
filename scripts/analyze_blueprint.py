import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

def analyze_blueprint(volume_id):
    print(f"--- Analyzing Blueprint: {volume_id} ---")
    try:
        res = supabase.table("Nodes").select("*").eq("volume_id", volume_id).order("created_at").execute()
        nodes = res.data
        print(f"Found {len(nodes)} nodes.\n")
        
        for i, n in enumerate(nodes):
            # Safe dict access
            content = n.get('content')
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    pass
            
            summary = "No summary"
            if isinstance(content, dict):
                summary = content.get('summary', 'No summary key')
            
            print(f"Node {i+1}: {n.get('title', 'No Title')}")
            print(f"Summary: {summary}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ID from previous step
    analyze_blueprint("6252b4d6-4e46-43d1-b9c5-a8af0a7b1b75")
