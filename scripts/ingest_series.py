import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from celery import Celery
import re

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

def extract_index_from_filename(filename: str) -> int:
    """
    Extracts a numeric index from filenames like 'Video - 1 of 15 - Title.txt'
    """
    match = re.search(r'\b(\d+)(?: of \d+)?\b', filename)
    if match:
        return int(match.group(1))
    return 9999 # Return a high number to push unindexed files to the end

def ingest_series_transcripts(directory_path, series_title, user_id):
    if not os.path.isdir(directory_path):
        print(f"Error: Directory '{directory_path}' not found.")
        return

    print(f"--- Starting series ingestion for '{series_title}' ---")

    # 1. Create a new Series entry
    series_data = {
        "user_id": user_id,
        "title": series_title,
        "description": f"Transcripts from the '{series_title}' playlist."
    }
    try:
        res = supabase.table("Series").insert(series_data).execute()
        if not res.data:
            print("Error: Series insert returned no data.")
            return
        series_id = res.data[0]['id']
        print(f"Successfully created Series ID: {series_id}")
    except Exception as e:
        print(f"Database Error creating Series: {e}")
        return

    # 2. Collect and sort transcript files
    transcript_files = []
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(".txt"):
            transcript_files.append(os.path.join(directory_path, filename))
    
    # Sort files numerically based on extracted index, then alphabetically
    transcript_files.sort(key=lambda f: (extract_index_from_filename(os.path.basename(f)), os.path.basename(f)))

    if not transcript_files:
        print(f"No .txt files found in '{directory_path}'.")
        return

    print(f"Found {len(transcript_files)} transcripts. Ingesting sequentially...")

    # 3. Ingest each transcript sequentially
    for i, file_path in enumerate(transcript_files):
        series_index = i + 1
        print(f"Processing ({series_index}/{len(transcript_files)}): '{os.path.basename(file_path)}'")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            print(f"Warning: File '{os.path.basename(file_path)}' is empty. Skipping.")
            continue

        # Generate a title from filename
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
        
        # Check for duplicates (simple check by title within the series)
        existing = supabase.table("Sources").select("id").eq("title", title).eq("user_id", user_id).eq("series_id", series_id).execute()
        if existing.data:
            print(f"Warning: Source '{title}' already exists in this series (ID: {existing.data[0]['id']}). Skipping.")
            continue

        # Create Source Record
        source_data = {
            "user_id": user_id,
            "raw_text": content,
            "title": title,
            "series_id": series_id,
            "series_index": series_index,
            "metadata": {
                "source": "local_series_upload",
                "original_filename": filename,
                "ingested_at": datetime.now().isoformat(),
                "series_title": series_title,
                "series_index": series_index,
                "youtube_video_id": f"local_series_{series_id}_{series_index}" # Placeholder
            }
        }
        
        try:
            res = supabase.table("Sources").insert(source_data).execute()
            if not res.data:
                print(f"Error: Insert for '{title}' returned no data.")
                continue
            
            source_id = res.data[0]['id']
            print(f"Successfully created Source ID: {source_id} for '{title}'")

            # Trigger the Indexing Agent with series context
            print(f"Triggering 'agents.indexing.run' for source {source_id} (Series Index: {series_index})...")
            celery_app.send_task('agents.indexing.run', args=[source_id, user_id])
            print("Task sent to worker queue!")

        except Exception as e:
            print(f"Database Error for '{title}': {e}")
    
    print(f"--- Series ingestion for '{series_title}' complete! ---")
    print("Check the worker logs to see the indexing progress for all sources.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a directory of text transcripts as a sequential Series and trigger indexing.")
    parser.add_argument("directory", help="Path to the directory containing text transcript files.")
    parser.add_argument("--series_title", required=True, help="Title of the series (e.g., 'Merkavah Mysticism Seminar').")
    parser.add_argument("--user_id", help="Specific User UUID (optional). Auto-detects if omitted.")
    
    args = parser.parse_args()

    uid = args.user_id or get_user_id()
    if not uid:
        sys.exit(1)
    
    print(f"Using User ID: {uid}")
    
    ingest_series_transcripts(args.directory, args.series_title, uid)
