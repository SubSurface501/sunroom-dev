import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from celery import Celery

# Add project root to path to ensure imports work if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
celery_app = Celery('sunroom-client', broker=CELERY_BROKER_URL)

def get_user_id():
    """Heuristic to find a valid User ID to attach the source to."""
    # 1. Try User_Integrations (most likely to have the active user)
    res = supabase.table("User_Integrations").select("user_id").limit(1).execute()
    if res.data:
        return res.data[0]['user_id']
    
    # 2. Try Sources
    res = supabase.table("Sources").select("user_id").limit(1).execute()
    if res.data:
        return res.data[0]['user_id']
        
    print("No user found in database. You must provide one manually.")
    uid = input("Enter User UUID: ").strip()
    if not uid:
        print("User ID is required.")
        sys.exit(1)
    return uid

def ingest_transcript(file_path, user_id):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    print(f"Reading '{file_path}'...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        print("Error: File is empty.")
        return

    # Generate a title from filename
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    
    print(f"Preparing to ingest as: '{title}'")

    # Check for duplicates (simple check by title)
    existing = supabase.table("Sources").select("id").eq("title", title).eq("user_id", user_id).execute()
    if existing.data:
        print(f"Warning: A source with title '{title}' already exists (ID: {existing.data[0]['id']}).")
        overwrite = input("Continue and create duplicate? (y/n): ")
        if overwrite.lower() != 'y':
            print("Aborted.")
            return

    # Create Source Record
    source_data = {
        "user_id": user_id,
        "raw_text": content,
        "title": title,
        "metadata": {
            "source": "local_upload",
            "original_filename": filename,
            "ingested_at": datetime.now().isoformat(),
            # We add a fake video ID so it doesn't break agents that expect one, 
            # though we should fix agents to be more robust.
            "youtube_video_id": f"local_{int(datetime.now().timestamp())}" 
        }
    }
    
    try:
        res = supabase.table("Sources").insert(source_data).execute()
        if not res.data:
            print("Error: Insert returned no data.")
            return
        
        source_id = res.data[0]['id']
        print(f"Successfully created Source ID: {source_id}")

        # Trigger the Indexing Agent
        print(f"Triggering 'agents.indexing.run' for source {source_id}...")
        celery_app.send_task('agents.indexing.run', args=[source_id, user_id])
        print("Task sent to worker queue!")
        print("Check the worker logs to see the indexing progress.")

    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a local text file as a Source and trigger indexing.")
    parser.add_argument("file", help="Path to the text transcript file.")
    parser.add_argument("--user_id", help="Specific User UUID (optional). Auto-detects if omitted.")
    
    args = parser.parse_args()

    uid = args.user_id or get_user_id()
    print(f"Using User ID: {uid}")
    
    ingest_transcript(args.file, uid)
