
import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client
from celery import Celery

# Import the transcription function
# Ensure the current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transcribe_local_video import transcribe_file, check_dependencies

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, CELERY_BROKER_URL]):
    print("Error: Missing environment variables (SUPABASE_URL, SUPABASE_SERVICE_KEY, CELERY_BROKER_URL)")
    sys.exit(1)

# Initialize Clients
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
celery_app = Celery('sunroom_tasks', broker=CELERY_BROKER_URL, backend='rpc://')

def ingest_directory(root_path, user_id, model_size="base"):
    print(f"--- Starting Ingestion for: {root_path} ---")
    print(f"User ID: {user_id}")
    
    if not check_dependencies():
        return

    supported_exts = ('.mp3', '.mp4', '.m4a', '.wav', '.mov', '.mkv')
    
    for root, dirs, files in os.walk(root_path):
        # Determine Playlist Name from the folder name
        # If root_path is C:\Media, and we are in C:\Media\Gnosticism, playlist is "Gnosticism"
        # If we are in the root_path itself, playlist is "Uncategorized" or the root folder name
        
        rel_path = os.path.relpath(root, root_path)
        if rel_path == ".":
            playlist_name = os.path.basename(root_path)
        else:
            playlist_name = os.path.basename(root) # Take the immediate parent folder name
            
        print(f"\n--- Scanning Folder: {playlist_name} ---")

        for file in files:
            if file.lower().endswith(supported_exts):
                file_path = os.path.join(root, file)
                print(f"Found: {file}")

                # 1. Check DB for duplicates
                # We check if a source exists with this filename and playlist metadata
                # This prevents re-transcribing and re-ingesting the same file.
                # Note: querying metadata jsonb can be tricky, simpler to check title match + user_id first
                
                existing = supabase.table("Sources").select("id, metadata").eq("user_id", user_id).eq("title", file).execute()
                
                is_duplicate = False
                if existing.data:
                    for row in existing.data:
                        if row['metadata'].get('playlist') == playlist_name:
                            print(f"  -> Skipping (Already Ingested as {row['id']})")
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    continue

                # 2. Transcribe
                # Check if transcript txt already exists to skip Whisper if run previously
                txt_path = os.path.splitext(file_path)[0] + ".txt"
                transcript_text = ""
                
                if os.path.exists(txt_path):
                    print(f"  -> Found existing transcript file: {txt_path}")
                    try:
                        with open(txt_path, "r", encoding="utf-8") as f:
                            transcript_text = f.read()
                    except Exception as e:
                        print(f"  -> Error reading transcript: {e}")
                
                if not transcript_text:
                    print(f"  -> Transcribing...")
                    created_txt_path = transcribe_file(file_path, model_name=model_size)
                    if created_txt_path:
                        with open(created_txt_path, "r", encoding="utf-8") as f:
                            transcript_text = f.read()
                    else:
                        print("  -> Transcription Failed.")
                        continue

                if not transcript_text.strip():
                    print("  -> Warning: Transcript is empty.")
                    continue

                # 3. Insert into DB
                print(f"  -> Inserting into Database...")
                source_data = {
                    "user_id": user_id,
                    "title": file,
                    "raw_text": transcript_text,
                    "metadata": {
                        "filename": file,
                        "playlist": playlist_name,
                        "file_path": file_path,
                        "source_type": "local_audio_ingest"
                    }
                }
                
                try:
                    res = supabase.table("Sources").insert(source_data).execute()
                    if res.data:
                        source_id = res.data[0]['id']
                        print(f"  -> Created Source ID: {source_id}")
                        
                        # 4. Dispatch Indexing Agent
                        print(f"  -> Dispatching Indexing Agent...")
                        celery_app.send_task('agents.indexing.run', args=[source_id, user_id])
                    else:
                        print("  -> DB Insert Failed (No data returned).")
                except Exception as e:
                    print(f"  -> DB Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a local directory of audio files, organized by folder (playlist).")
    parser.add_argument("path", help="Path to the root directory containing audio files/folders")
    parser.add_argument("user_id", help="The Supabase User ID to assign these sources to")
    parser.add_argument("--model", default="base", help="Whisper model size")
    
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' not found.")
        sys.exit(1)
        
    ingest_directory(args.path, args.user_id, args.model)
