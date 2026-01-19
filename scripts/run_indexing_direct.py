import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from worker.src.agents.indexing import IndexAtomAgent
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

# IDs from the previous ingestion step
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
SOURCE_ID = "b75d0dfe-fc5a-42b0-be98-2780f9ed1c58"

def run_indexing():
    print(f"Running IndexAtomAgent directly...")
    print(f"User: {USER_ID}")
    print(f"Source: {SOURCE_ID}")
    
    agent = IndexAtomAgent(db=db_client, worker=None, llm=llm_client)
    agent.run_task(source_id=SOURCE_ID, user_id=USER_ID)
    
    print("Indexing complete.")

if __name__ == "__main__":
    run_indexing()
