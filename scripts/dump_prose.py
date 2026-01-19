import os
import sys
import logging
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.session import get_db
from dotenv import load_dotenv

load_dotenv()

def dump_volume_content(volume_id):
    db = get_db()
    print(f"--- DUMPING VOLUME {volume_id} ---")
    
    # Fetch all nodes
    try:
        res = db.table("Nodes").select("title, content").eq("volume_id", volume_id).order("created_at").execute()
        nodes = res.data
        
        for i, node in enumerate(nodes):
            print(f"\n=== NODE {i+1}: {node.get('title', 'Untitled')} ===")
            content = node.get('content', {})
            
            # Check Summary
            print(f"SUMMARY: {content.get('summary', 'N/A')}\n")
            
            # Check Pages
            pages = content.get('pages', [])
            if not pages:
                print("(No pages generated)")
            
            for p_idx, page in enumerate(pages):
                text = page.get('narrative_text', '')
                print(f"-- Page {p_idx+1} --")
                print(text)
                print("------\n")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_volume_content("71390e7c-fec6-4178-8e80-d368ee9e1ad9")
