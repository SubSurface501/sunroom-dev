import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

def check_table(table_name):
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        cur.execute(f"SELECT to_regclass('public.{table_name}');")
        result = cur.fetchone()[0]
        
        if result:
            print(f"Table 'public.{table_name}' exists.")
        else:
            print(f"Table 'public.{table_name}' does NOT exist.")
            
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table("AtomEdges")
