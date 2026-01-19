import sys
import os
import asyncio
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
load_dotenv(os.path.join(project_root, '.env'))

from worker.src.agents.tasks import generate_constrained_thought

# Configuration
TEST_PROMPT = "The impact of quantum coherence on biological systems"
# Using the valid user ID we found earlier
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" 
VOLUME_ID = "vol_test_123" # Mock volume

def main():
    print(f"🧠 Triggering EBM-CoT Loop for prompt: '{TEST_PROMPT}'")
    print("-------------------------------------------------------")
    
    # We call the function directly (bypassing Celery broker for testing)
    result = generate_constrained_thought(TEST_PROMPT, USER_ID, VOLUME_ID)
    
    print("-------------------------------------------------------")
    print(f"🏁 Result: {result}")

if __name__ == "__main__":
    main()
