import os
import logging
import psycopg2
from dotenv import load_dotenv

# Load env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("SUPABASE_DB_URL")

def main():
    if not DB_URL:
        logger.error("SUPABASE_DB_URL not found in .env")
        return

    logger.info("Connecting to Database...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        sql = "ALTER TYPE source_type_enum ADD VALUE IF NOT EXISTS 'uploaded_audio';"
            
        logger.info(f"Executing: {sql}")
        cursor.execute(sql)
        
        logger.info("✅ Enum updated successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Migration Failed: {e}")

if __name__ == "__main__":
    main()
