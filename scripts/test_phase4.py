import os
import uuid
import requests
from dotenv import load_dotenv

# Import your actual codebase
from db.session import get_db
from db import schemas # For Pydantic models
from worker.src.agents.tasks import generate_deep_synthesis
from llm.client import get_llm_client

# Load Environment (HF_TOKEN, DB_URL)
load_dotenv()

# Use a known good user_id from the logs, or modify setup_test_data to fetch/create one.
# For this test, we'll use the user that already has atoms from previous 'dreaming' run.
TEST_USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"

def setup_test_data(db_client):
    """Ensures we have a User, Project, and Atoms."""
    print("🛠️  Setting up Test Data...")
    
    user_id = TEST_USER_ID
    print(f"   -> Using Test User ID: {user_id}")
    
    # Get or Create a Test Project for this user
    project_id = None
    project_res = db_client.table("projects").select("id").eq("owner_id", user_id).limit(1).execute()
    if project_res.data:
        project_id = project_res.data[0]['id']
        print(f"   -> Using existing Project ID: {project_id}")
    else:
        print("   -> Creating Dummy Project")
        new_project_data = {
            "name": "Synthesis Lab",
            "owner_id": user_id
        }
        project_create_res = db_client.table("projects").insert(new_project_data).execute()
        project_id = project_create_res.data[0]['id']
        # Add owner as member automatically
        db_client.table("project_members").insert({"project_id": project_id, "user_id": user_id, "role": "architect"}).execute()
        print(f"   -> Created Project ID: {project_id}")

    # Ensure Persona Profile exists
    persona_res = db_client.table("persona_profiles").select("*").eq("user_id", user_id).execute()
    if not persona_res.data:
        print("   -> Creating default Persona Profile")
        profile_data = {
            "user_id": user_id,
            "system_prompt_cache": "You are a meticulous researcher with a flair for dramatic storytelling. Worldview: Rationalist but open to the mystical.",
            "fidelity_weight": 0.8
        }
        db_client.table("persona_profiles").insert(profile_data).execute()

    return user_id, project_id

def ensure_knowledge_atoms(db_client, user_id, project_id):
    """Inserts dummy atoms if none exist, so the Scribe has something to write about."""
    # Check for existing atoms
    atoms_res = db_client.table("Atoms").select("id").eq("user_id", user_id).limit(1).execute()
    if not atoms_res.data:
        print("   -> No atoms found. Seeding dummy knowledge.")
        client = get_llm_client()
        
        dummy_data = [
            ("JFK Speech", "Ask not what your country can do for you, ask what you can do for your country.", "Civic Duty"),
            ("Moon Landing", "We choose to go to the moon in this decade and do the other things, not because they are easy, but because they are hard.", "Ambition"),
            ("Cold War Context", "The speech was given during the height of the Cold War, serving as a call for unity against a common global threat.", "Historical Context")
        ]
        
        for name, content, instruction in dummy_data:
            embedding = client.get_embedding(content)
            atom = {
                "user_id": user_id,
                "name": name,
                "content": content,
                "meta_instruction": instruction,
                "type": "concept",
                "embedding": embedding,
                "metadata": {"project_id": project_id}
            }
            db_client.table("Atoms").insert(atom).execute()
        print("   -> Seeded 3 dummy atoms.")
    else:
        print("   -> Knowledge atoms already exist.")

def run_test():
    db = get_db()
    
    try:
        # 1. Prepare Environment
        user_id, project_id = setup_test_data(db)
        ensure_knowledge_atoms(db, user_id, project_id)

        # 2. Construct Payload
        prompt = "Write a deep analysis of JFK's rhetoric and its impact on the American psyche."
        payload = {
            "user_id": user_id,
            "project_id": project_id,
            "prompt": prompt
        }

        print(f"\n🚀 STARTING DEEP SYNTHESIS: '{prompt}'")
        
        # 3. Trigger Task
        result = generate_deep_synthesis(payload)
        
        print("\n✅ TASK COMPLETED.")
        print(f"   Status: {result['status']}")
        print(f"   Manifest: {len(result['manifest'])} chapters")
        print("\n--- PREVIEW ---")
        print(result['preview'])
        print("\n--- END PREVIEW ---")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
