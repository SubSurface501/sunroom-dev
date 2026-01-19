import argparse
import os
import sys
from dotenv import load_dotenv
from typing import Optional, List
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from supabase import create_client, Client
from llm.client import LLMClient
from worker.src.agents.batch_producer import BatchProducerAgent
from worker.src.agents.crystallize import CrystallizeVolumeAgent
from db.session import get_db

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

def run_full_render_test(volume_id: str, user_id: str, debug: bool, universe_ids: Optional[List[str]] = None, target_length: int = 12, storyline_id: Optional[str] = None):
    """
    Runs a full render test on a specific volume.
    """
    print(f"--- Starting Full Render Test ---")
    print(f"Volume ID: {volume_id}")
    print(f"User ID: {user_id}")
    print(f"Debug Mode: {debug}")
    print(f"Universe IDs: {universe_ids}")
    print(f"Storyline ID: {storyline_id}")
    print("---------------------------------")

    # 1. Initialize Clients
    db = get_db()
    llm = LLMClient(debug_mode=debug)
    
    mock_worker = None

    # 2. Instantiate BatchProducerAgent
    producer = BatchProducerAgent(db, mock_worker, llm)

    # 3. Modify StorybookAgent for faster debug runs
    if debug:
        print("Debug mode: LLM calls and Image Generation will be mocked.")
        # In a real test suite, you might monkeypatch the agent, but for now we rely on the LLM mock
        # and the fact that the mock outline is short.

    # 4. Run the task
    try:
        producer.run_task(
            volume_id, 
            mode="full_render", 
            user_id=user_id, 
            universe_ids=universe_ids, 
            target_length=target_length,
            storyline_id=storyline_id,
            is_test_run=True # Prevent async finalization
        )
        
        # 5. Synchronous Crystallization for Testing
        print("\n--- Synchronously Crystallizing Volume for Verification ---")
        crystallizer = CrystallizeVolumeAgent(db, mock_worker, llm)
        crystallizer.run_task(volume_id=volume_id)
        
        print("\n--- Test Run Completed Successfully ---")
    except Exception as e:
        print(f"\n--- Test Run Failed ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a full render test for a story volume.")
    parser.add_argument("volume_id", type=str, help="The ID of the story volume to test.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode to mock expensive API calls.")
    parser.add_argument("--universe_ids", nargs='*', help="A list of universe IDs to scope the run.")
    
    args = parser.parse_args()

    # Hardcoded user_id for testing
    user_id = "75dadbbc-34da-4cb3-a75d-edaa5dcf7341"

    run_test(args.volume_id, user_id, args.debug, args.universe_ids)
