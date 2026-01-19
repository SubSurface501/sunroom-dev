import sys
import os
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.src.agents.tasks import generate_constrained_thought
from db.session import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)

def run_test():
    load_dotenv()
    
    # 1. Get a test user
    # We'll just use a hardcoded UUID or try to find one.
    # For safety, let's look for a user in the DB.
    db = get_db()
    
    # Try to find a user
    # res = db.table("auth.users").select("id").limit(1).execute() # auth.users is usually protected
    # Try public table if any? "Atoms"?
    res = db.table("Atoms").select("user_id").limit(1).execute()
    
    if not res.data:
        print("No users found to test with.")
        return

    user_id = res.data[0]['user_id']
    print(f"Testing with User ID: {user_id}")
    
    # 2. Run the Task
    prompt = "The impact of quantum coherence on biological systems"
    
    # We pass a fake volume_id or None. The code handles None (empty trajectory).
    # But to test Gamma, we ideally want a volume.
    # Let's try with None first.
    print(f"--- Running EBM Loop for: '{prompt}' ---")
    try:
        result = generate_constrained_thought(prompt, user_id, volume_id="test_vol_123")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
