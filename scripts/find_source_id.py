import os
import sys
from dotenv import load_dotenv
from db.session import get_db
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

def find_glitch_bottle_source():
    db = get_db()
    try:
        # Search for 'Glitch Bottle' in the title or raw_text of the Sources table
        # Note: This assumes a 'Sources' table exists and is accessible via SQL.
        # The 'sources' table name might be lowercase or capitalized depending on your DB schema.
        sql = text("SELECT id, title FROM \"Sources\" WHERE title ILIKE '%Glitch Bottle%' OR raw_text ILIKE '%Glitch Bottle%' LIMIT 1")
        result = db.execute(sql).fetchone()
        
        if result:
            print(f"Found Source ID: {result[0]}")
            print(f"Title: {result[1]}")
            return str(result[0])
        else:
            print("No source found matching 'Glitch Bottle'.")
            return None
    except Exception as e:
        print(f"Database query failed: {e}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    find_glitch_bottle_source()
