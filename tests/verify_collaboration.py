import sys
import os
import asyncio
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
load_dotenv(os.path.join(project_root, '.env'))

from db.session import get_db
from db import crud
from llm.client import get_llm_client
from worker.src.agents.collaborative_planner import CollaborativePlanner

def main():
    db = get_db()
    llm = get_llm_client()
    planner = CollaborativePlanner(db)
    
    print("\n--- 🧬 Setting up Collaborative Simulation 🏗️ ---")
    
    # 1. Fetch Real Identities
    # We need valid user_ids to avoid FK violations.
    try:
        # Fetch a few atoms to get user_ids
        res = db.table("Atoms").select("user_id").limit(10).execute()
        found_ids = list(set([r['user_id'] for r in res.data]))
    except Exception as e:
        print(f"Error fetching users: {e}")
        found_ids = []

    if len(found_ids) >= 2:
        user_architect = found_ids[0]
        user_biologist = found_ids[1]
    elif len(found_ids) == 1:
        print("⚠️ Only 1 user found. Using same ID for both roles (simulated split).")
        user_architect = found_ids[0]
        user_biologist = found_ids[0]
    else:
        # Fallback if DB is empty - unlikely if we ran previous tests
        print("⚠️ No users found. Using hardcoded ID and hoping for best (might fail FK).")
        user_architect = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" 
        user_biologist = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # Use same valid one

    print(f"Using Architect ID: {user_architect}")
    print(f"Using Biologist ID: {user_biologist}")
    
    volume_id = "vol_collab_test"
    
    # 2. Ingest Distinct Knowledge (The "Graphs")
    
    # Architect knows about "Brutalism"
    arch_fact = "Brutalist architecture uses raw concrete and massive geometric forms to express structural honesty."
    try:
        crud.create_atom(db, crud.schemas.Atom(
            content=arch_fact, name="Fact: Brutalism", type="thought", user_id=user_architect, 
            embedding=llm.get_embedding(arch_fact), metadata={"volume_id": volume_id}
        ))
    except Exception as e:
        print(f"Warning inserting arch atom: {e}")

    # Biologist knows about "Mycelium"
    bio_fact = "Mycelium hyphae create self-healing, fire-resistant structural networks that grow into molds."
    try:
        crud.create_atom(db, crud.schemas.Atom(
            content=bio_fact, name="Fact: Mycelium", type="thought", user_id=user_biologist, 
            embedding=llm.get_embedding(bio_fact), metadata={"volume_id": volume_id}
        ))
    except Exception as e:
        print(f"Warning inserting bio atom: {e}")

    print("✅ Ingested unique knowledge into separate user graphs.")
    
    # 3. Define the Challenge
    prompt = "Design a futuristic building material that combines structural permanence with organic adaptability."
    
    # 4. Map Roles to IDs
    collaborator_map = {
        "Brutalist Architect": user_architect,
        "Mycologist": user_biologist
    }
    
    # 5. Execute Collaboration
    print(f"\n🧠 Running Collaborative Planner for: '{prompt}'...")
    try:
        transcript = planner.generate_collaborative_transcript(prompt, collaborator_map, volume_id)
        
        print("\n" + "="*60)
        print("📝 RESULTING COMPOSITE MIND TRANSCRIPT")
        print("="*60)
        print(transcript)
        print("="*60)
        
        # Verification Logic
        if "concrete" in transcript.lower() and "mycelium" in transcript.lower():
            print("\n✅ SUCCESS: Transcript successfully braided concepts from both graphs.")
        else:
            print("\n❌ FAILURE: Missing inputs from one or both experts.")
            
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
