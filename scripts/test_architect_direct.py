import os
from db.session import get_db
from worker.src.agents.architect_v2 import VolumeArchitectAgent
from llm.client import get_llm_client
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

def test_architect_direct():
    print("--- Testing Architect Agent Directly ---")
    
    # 1. Setup
    db = get_db()
    llm = get_llm_client()
    
    # Mock worker (we don't need actual celery for this unit test)
    class MockWorker:
        def send_task(self, name, args=None, kwargs=None):
            print(f"MockWorker: Sending task {name} with {args}")
            return None
            
    worker = MockWorker()
    
    # 2. Find a User
    print("Finding user...")
    user_res = db.table("Sources").select("user_id").limit(1).execute()
    if not user_res.data:
        print("No user found in Sources, checking StoryVolumes...")
        user_res = db.table("StoryVolumes").select("user_id").limit(1).execute()
        
    if not user_res.data:
        print("CRITICAL: No users found in DB. Cannot test.")
        return
        
    user_id = user_res.data[0]['user_id']
    print(f"Using User ID: {user_id}")
    
    # 3. Initialize Agent
    architect = VolumeArchitectAgent(db, worker, llm)
    
    # 4. Run Task (Drafting)
    theme = "A Cyberpunk Detective investigating a Digital Ghost"
    root_concept = "The Ghost in the Machine"
    
    print(f"Drafting volume for theme: {theme}")
    try:
        volume_id = architect.run_task(user_id, theme, depth=3) # Low depth for speed
        print(f"\nSUCCESS! Volume Drafted. ID: {volume_id}")
        
        # 5. Verify Output
        vol_data = db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
        print(f"Volume Title: {vol_data.data['title']}")
        print(f"Graph Nodes: {len(vol_data.data['graph_structure']['nodes'])}")
        
        # Check Connections for Joint Types
        conns = vol_data.data['graph_structure']['connections']
        print(f"Connections: {len(conns)}")
        if conns:
            print(f"Sample Joint Type: {conns[0].get('joint_type', 'N/A')}")
            
    except Exception as e:
        print(f"FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_architect_direct()
