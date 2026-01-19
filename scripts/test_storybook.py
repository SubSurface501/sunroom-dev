import os
import sys
import logging
import json
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from worker.src.agents.storybook import StorybookAgent
from llm.client import LLMClient

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    sys.exit(1)

db_client = create_client(SUPABASE_URL, SUPABASE_KEY)
llm_client = LLMClient()

# IDs
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
TRAILHEAD_ID = "82d74776-cbce-494e-b1f4-df80fc51d57a"

def run_test():
    print(f"Running StorybookAgent test...")
    print(f"User: {USER_ID}")
    print(f"Trailhead: {TRAILHEAD_ID}")
    
    agent = StorybookAgent(db=db_client, worker=None, llm=llm_client)
    manifest = agent.run_task(user_id=USER_ID, trailhead_id=TRAILHEAD_ID)
    
    if manifest:
        print("\n--- STORYBOOK GENERATED ---\n")
        print(json.dumps(manifest, indent=2))
    else:
        print("Failed to generate storybook.")

if __name__ == "__main__":
    run_test()
