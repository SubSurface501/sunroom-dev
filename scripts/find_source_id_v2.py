import os
import sys
from dotenv import load_dotenv
from db.session import get_db

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def find_glitch_bottle_source():
    db = get_db() # Returns Supabase Client
    try:
        # Use Supabase client syntax
        # Search for 'Glitch Bottle' in the title
        response = db.table("Sources").select("id, title").ilike("title", "%Glitch Bottle%").limit(1).execute()
        
        if response.data:
            result = response.data[0]
            print(f"Found Source ID: {result['id']}")
            print(f"Title: {result['title']}")
            return result['id']
        else:
            print("No source found matching 'Glitch Bottle' in title.")
            # Try content search if title fails, though slower
            # response = db.table("Sources").select("id, title").ilike("raw_text", "%Glitch Bottle%").limit(1).execute()
            # ... logic for content search ...
            return None
            
    except Exception as e:
        print(f"Database query failed: {e}")
        return None

if __name__ == "__main__":
    find_glitch_bottle_source()