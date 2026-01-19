import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL") # Corrected to SUPABASE_DB_URL based on .env

def apply_migration(file_path):
    print(f"⚡ Connecting to Database...")
    
    # Connect to Supabase
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print(f"📖 Reading migration file: {file_path}")
        with open(file_path, 'r') as f:
            sql_content = f.read()
            
        print(f"🚀 Executing SQL...")
        cur.execute(sql_content)
        conn.commit()
        
        print(f"✅ Migration {file_path} applied successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <path_to_sql_file>")
    else:
        apply_migration(sys.argv[1])