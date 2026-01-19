
import os
import json
import logging
from dotenv import load_dotenv
from llm.client import get_llm_client
import prompts

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

print("--- Testing Story Suggestions ---")

# Mock Context
library_context = """
Existing Story Volumes:
- Title: The Lost City of Gold, Root: Alchemy
Interesting Trailheads:
- The Emerald Tablet
"""

try:
    print("1. Initializing LLM Client...")
    llm = get_llm_client()
    print("   [OK] Initialized.")

    print("2. Generating Suggestions...")
    prompt = prompts.STORY_SUGGESTION_PROMPT.format(library_context=library_context)
    
    print(f"   Prompt Length: {len(prompt)} chars")
    
    response_json = llm.chat_completion(prompt)
    print("\n   [OK] Raw Response Received:")
    print(response_json[:500] + "..." if len(response_json) > 500 else response_json)
    
    # Parse
    suggestions = json.loads(response_json)
    print(f"\n   [OK] Parsed {len(suggestions)} suggestions.")
    for s in suggestions:
        print(f"   - {s.get('theme')}")

except Exception as e:
    print(f"\n[ERROR] Failed: {e}")
