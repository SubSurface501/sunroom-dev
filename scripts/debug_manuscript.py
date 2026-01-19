import os
import sys

# Correctly add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from db.supabase_client import get_supabase_client

def debug_node_pages(node_id: str):
    db = get_supabase_client()
    res = db.table("Nodes").select("title, content").eq("id", node_id).single().execute()
    node = res.data
    print(f"DEBUGGING PAGES FOR: {node['title']}")
    pages = node['content'].get('pages', [])
    print(f"Number of pages: {len(pages)}")
    for i, page in enumerate(pages):
        print(f"  Page {i+1} keys: {page.keys()}")
        for key in ['narrative_text', 'text', 'content', 'prose']:
            if key in page:
                val = str(page[key])
                print(f"    Found '{key}' ({len(val)} chars): {val[:200]}...")

if __name__ == "__main__":
    # Use one of the node IDs that has 'pages'
    # From previous output: The Merchant's Call (b0fe84c6-4a25-4e27-9028-fbcf657e21e5)
    debug_node_pages("b0fe84c6-4a25-4e27-9028-fbcf657e21e5")
