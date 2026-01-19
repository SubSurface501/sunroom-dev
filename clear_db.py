import os
import sys
from dotenv import load_dotenv

# Ensure the project root is in sys.path for module imports
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, '.env'))

from db.session import get_db

def clear_tables():
    db = get_db()
    
    print("Clearing 'Atoms' table...")
    # Using .neq("id", "000...") to avoid issues with RLS and to ensure deletion of all actual entries.
    db.table("Atoms").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("All rows deleted from 'Atoms'.")

    print("Clearing 'Sources' table...")
    db.table("Sources").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("All rows deleted from 'Sources'.")

    print("Database cleared successfully for testing!")

if __name__ == "__main__":
    clear_tables()
