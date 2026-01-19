import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from worker.src.agents.youtube_ideation import GeneratePerformanceDrivenIdeasAgent
from worker.src.agents.indexing import IndexAtomAgent # Import strictly for type checking if needed, or remove
from llm.client import get_llm_client
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def run_test():
    print("--- Setting up Test Environment ---")
    
    # 1. Get User
    user_res = supabase.table("User_Integrations").select("user_id").limit(1).execute()
    if not user_res.data:
        print("No user found. Please ensure a user exists.")
        return
    user_id = user_res.data[0]['user_id']
    print(f"User ID: {user_id}")

    # 2. Get Series (Merkavah)
    series_res = supabase.table("Series").select("id, title").ilike("title", "%Merkavah%").limit(1).execute()
    series_id = None
    if series_res.data:
        series_id = series_res.data[0]['id']
        print(f"Found Series: {series_res.data[0]['title']} ({series_id})")
    else:
        print("Warning: 'Merkavah' series not found. Running in global mode.")

    # 3. Initialize Agent
    # We mock the celery worker as we are running synchronously
    mock_worker = MagicMock()
    llm_client = get_llm_client()
    
    agent = GeneratePerformanceDrivenIdeasAgent(db=supabase, worker=mock_worker, llm=llm_client)

    print("\n--- Running Ideation Agent ---")
    print("(Check logs for 'Frontier Atlas')\n")
    
    agent.run_task(
        user_id=user_id, 
        series_id=series_id, 
        focus_area="The intersection of Magic and Mysticism", 
        depth="Advanced"
    )
    
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    run_test()
