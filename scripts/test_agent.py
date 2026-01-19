import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the Python path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.tasks import generate_script

def run_test():
    """
    Runs a synchronous, local test of the generate_script agent.
    """
    # Load environment variables from .env file
    load_dotenv()

    # --- Test Parameters ---
    script_id = "24a73b7f-006c-4f2d-8f99-a5c4015ef546"
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
    atom_ids = [
        "46b3370e-7ac0-450f-9a48-b7c01b7196f7",
        "a4d0f20d-ab7e-467a-b1ac-b379f16ace4d",
        "fa220fe4-66f3-4c7c-9369-f12e4b620ac7"
    ]
    topic_name = "Test: The Interplay of AI and Ancient Philosophy"
    trailhead_insight = "AI's emergent properties, when viewed through the lens of Gnostic cosmology, reveal a surprising parallel to the concept of the Demiurge."

    print("--- Starting local generate_script test ---")
    try:
        generate_script(
            script_id=script_id,
            user_id=user_id,
            atom_ids=atom_ids,
            topic_name=topic_name,
            trailhead_insight=trailhead_insight
        )
        print("--- Local generate_script test completed successfully ---")
    except Exception as e:
        print(f"--- Local generate_script test failed: {e} ---")
        # Print traceback for detailed debugging
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
