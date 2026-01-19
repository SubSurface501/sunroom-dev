import os
import sys
import json
from dotenv import load_dotenv
from supabase import create_client

# Add project root to sys.path
sys.path.append(os.getcwd())

load_dotenv()

def inspect_volumes():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    supabase = create_client(url, key)

    # 1. Fetch Epochs to see the intended arc
    print("--- EPOCH DEFINITIONS (The Plan) ---")
    epochs = supabase.table("Epochs").select("id, name, seed_prose").order("id").execute().data
    for e in epochs:
        seed_prose_preview = (e.get('seed_prose') or "")[:100]
        print(f"Epoch {e['id']} ({e['name']}): {seed_prose_preview}...")

    # 2. Fetch recent Volumes
    print("\n--- RECENT VOLUMES (The Execution) ---")
    # Fetch last 3 volumes
    vols = supabase.table("StoryVolumes").select("id, title, root_concept, universe_id, storyline_id, created_at").order("created_at", desc=True).limit(3).execute().data
    
    for v in vols:
        print(f"\nVolume ID: {v['id']}")
        print(f"Title: {v['title']}")
        print(f"Concept: {v['root_concept']}")
        
        # Get Nodes for this volume to check the prose "Leak"
        nodes = supabase.table("Nodes").select("title, content").eq("volume_id", v['id']).execute().data
        nodes.sort(key=lambda x: x['content'].get('page_number', 0) if isinstance(x['content'], dict) else 0)
        
        print("  -- Nodes/Pages --")
        for n in nodes:
            content = n['content']
            if isinstance(content, str):
                try: content = json.loads(content)
                except: content = {}
            
            page_num = content.get('page_number', '?')
            summary = content.get('summary', '')[:100]
            text = content.get('narrative_text', '')[:100]
            print(f"  Page {page_num}: {n['title']} -> {text}...")

if __name__ == "__main__":
    inspect_volumes()
