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

def run_saga_test():
    print(f"Running StorybookAgent SAGA test...")
    print(f"User: {USER_ID}")
    print(f"Trailhead: {TRAILHEAD_ID}")
    
    agent = StorybookAgent(db=db_client, worker=None, llm=llm_client)
    # Requesting 12 pages for this test
    manifest = agent.run_task(user_id=USER_ID, trailhead_id=TRAILHEAD_ID, target_length=12)
    
    if manifest:
        print("\n--- SAGA GENERATED ---\n")
        print(f"Title: {manifest.get('project_title')}")
        print(f"Total Pages: {len(manifest.get('pages', []))}")
        # Print first and last page summaries to verify arc
        if len(manifest['pages']) > 0:
            print(f"Page 1: {manifest['pages'][0].get('narrative_text')[:100]}...")
            print(f"Page {len(manifest['pages'])}: {manifest['pages'][-1].get('narrative_text')[:100]}...")
    else:
        print("Failed to generate saga.")

if __name__ == "__main__":
    run_saga_test()
