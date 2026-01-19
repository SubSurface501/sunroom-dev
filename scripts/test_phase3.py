import os
import uuid
import requests
from dotenv import load_dotenv

# Import your actual codebase
from db.session import get_db
from db import schemas # For Pydantic models
from worker.src.agents.tasks import process_upload  # Adjust import if you named the file differently

# Load Environment (HF_TOKEN, DB_URL)
load_dotenv()

# Configuration
TEST_AUDIO_URL = "https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav"
TEST_FILENAME = "test_jfk_speech.wav"
# Use a known good user_id from the logs, or modify setup_test_data to fetch/create one.
# For this test, we'll use the user that already has atoms from previous 'dreaming' run.
TEST_USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"

def setup_test_data(db_client):
    """Ensures we have a User, Project, and Source to attach data to using Supabase client."""
    print("🛠️  Setting up Test Data...")
    
    # 1. Use the pre-defined TEST_USER_ID
    user_id = TEST_USER_ID
    print(f"   -> Using Test User ID: {user_id}")
    
    # 2. Get or Create a Test Project for this user
    project_id = None
    project_res = db_client.table("projects").select("id").eq("owner_id", user_id).limit(1).execute()
    if project_res.data:
        project_id = project_res.data[0]['id']
        print(f"   -> Using existing Project ID: {project_id}")
    else:
        print("   -> Creating Dummy Project")
        new_project_data = {
            "name": "Audio Test Lab",
            "owner_id": user_id
        }
        project_create_res = db_client.table("projects").insert(new_project_data).execute()
        project_id = project_create_res.data[0]['id']
        # Add owner as member automatically (as in crud.create_project to ensure RLS works)
        db_client.table("project_members").insert({"project_id": project_id, "user_id": user_id, "role": "architect"}).execute()
        print(f"   -> Created Project ID: {project_id}")

    # 3. Create a Source Entry
    print("   -> Creating Source Entry")
    source_id = str(uuid.uuid4())
    source_data = {
        "id": source_id,
        "user_id": user_id, # Source requires user_id
        "title": TEST_FILENAME,
        "source_type": schemas.SourceType.UPLOADED_TEXT.value, # Arbitrary type, will be updated by process_upload
        "storage_path": os.path.abspath(TEST_FILENAME), # Store local path for worker to find
        "is_processed": False
    }
    source_create_res = db_client.table("Sources").insert(source_data).execute()
    if not source_create_res.data:
        raise Exception("Failed to create source in DB.")

    # 4. Create a dummy subscription for the user (Creator Tier for generous limits)
    print("   -> Ensuring active 'Creator' tier subscription")
    tier_res = db_client.table("tiers").select("id").eq("name", "Creator").single().execute()
    if not tier_res.data:
        raise Exception("'Creator' tier not found in the database. Please ensure migrations are up-to-date.")
    creator_tier_id = tier_res.data['id']

    # Check if user already has an active subscription
    sub_res = db_client.table("user_subscriptions").select("id").eq("user_id", user_id).eq("is_active", True).execute()
    if not sub_res.data:
        from datetime import datetime, timedelta, timezone
        # Create a subscription valid for the next year
        subscription_data = {
            "user_id": user_id,
            "tier_id": creator_tier_id,
            "cycle_start_date": datetime.now(timezone.utc).isoformat(),
            "cycle_end_date": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "is_active": True
        }
        db_client.table("user_subscriptions").insert(subscription_data).execute()
        print("   -> Created new 'Creator' tier subscription.")
    else:
        print("   -> User already has an active subscription.")

    return user_id, project_id, source_id


def download_sample_audio():
    """Downloads the JFK speech sample if not present."""
    if not os.path.exists(TEST_FILENAME):
        print(f"📥 Downloading sample audio from {TEST_AUDIO_URL}...")
        response = requests.get(TEST_AUDIO_URL)
        response.raise_for_status() # Raise an exception for HTTP errors
        with open(TEST_FILENAME, 'wb') as f:
            f.write(response.content)
        print("   -> Download Complete.")
    else:
        print("   -> Sample audio already exists.")

def run_test():
    db = get_db() # Get Supabase Client
    
    try:
        # 1. Prepare Environment
        download_sample_audio()
        user_id, project_id, source_id = setup_test_data(db)

        # 2. Construct the Payload (Simulating what the API sends to Celery)
        payload = {
            "user_id": user_id,
            "project_id": project_id,
            "source_id": source_id,
            "file_path": os.path.abspath(TEST_FILENAME),
            "file_type": "audio/wav" # Ensure this matches what process_upload expects
        }

        print("\n🚀 STARTING TASK EXECUTION (Direct Call)...")
        print(f"   Target: {TEST_FILENAME}")
        # The gatekeeper log will be in the process_upload output
        
        # 3. Trigger the Task Directly (Bypassing Celery Queue)
        # process_upload internally calls get_db(), so no need to pass db_client.
        result = process_upload(payload)
        
        print("\n✅ TASK COMPLETED.")
        print(f"   Result: {result}")

        # 4. Verify Database Integrity
        print("\n🔍 VERIFYING DATABASE:")
        
        # Check Atoms
        atom_count_res = db.table("Atoms").select("id", count="exact").eq("resolution_source_id", source_id).execute()
        atom_count = atom_count_res.count if atom_count_res.count is not None else 0
        print(f"   -> Atoms Created: {atom_count}")
        if atom_count > 0:
            sample_atom_res = db.table("Atoms").select("*").eq("resolution_source_id", source_id).limit(1).execute()
            if sample_atom_res.data:
                sample_atom = schemas.Atom(**sample_atom_res.data[0])
                print(f"   -> Sample Instruction: {sample_atom.meta_instruction[:100]}...")
            else:
                print("   ❌ ERROR: No sample atom data found after query.")

        # Check Usage Log
        usage_res = db.table("usage_logs").select("*").eq("user_id", user_id).eq("project_id", project_id).eq("activity_type", "PROCESS_MEDIA").order("created_at", desc=True).limit(1).execute()
        if usage_res.data:
            usage = schemas.UsageLog(**usage_res.data[0])
            print(f"   -> Ledger Charged: {usage.quantity_used} seconds (Activity: {usage.activity_type})")
        else:
            print("   ❌ ERROR: No usage log found for PROCESS_MEDIA!")
        
        # Check Source update
        source_update_res = db.table("Sources").select("is_processed", "media_duration_seconds").eq("id", source_id).single().execute()
        if source_update_res.data:
            print(f"   -> Source Updated: is_processed={source_update_res.data['is_processed']}, media_duration_seconds={source_update_res.data['media_duration_seconds']}")
        else:
            print("   ❌ ERROR: Source not found or not updated!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Supabase client doesn't need explicit close() like SQLAlchemy session
        pass


if __name__ == "__main__":
    run_test()
