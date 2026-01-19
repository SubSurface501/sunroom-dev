import os
import json
from dotenv import load_dotenv
from supabase import create_client
import google.genai as genai
import prompts
from llm.client import get_llm_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"GEMINI_API_KEY present: {bool(GEMINI_API_KEY)}")

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def test_suggestions():
    # 1. specific user ID or find one
    print("Finding a user...")
    # Try to find a user from Sources or StoryVolumes
    response = supabase.table("Sources").select("user_id").limit(1).execute()
    if not response.data:
        response = supabase.table("StoryVolumes").select("user_id").limit(1).execute()
    
    if not response.data:
        print("No users found with data. Using a dummy ID but context will be empty.")
        user_id = "dummy_user_id"
    else:
        user_id = response.data[0]['user_id']
        print(f"Found user_id: {user_id}")

    # 2. Gather Context
    print("Gathering context...")
    volumes_resp = supabase.from_("StoryVolumes").select("title, root_concept").eq("user_id", user_id).limit(5).execute()
    trailheads_resp = supabase.from_("Trailheads").select("title").eq("user_id", user_id).limit(10).execute()

    library_context = "Existing Story Volumes:\n"
    if volumes_resp.data:
        for v in volumes_resp.data:
            library_context += f"- Title: {v.get('title')}, Root: {v.get('root_concept')}\n"
    
    library_context += "\nInteresting Trailheads:\n"
    if trailheads_resp.data:
        for t in trailheads_resp.data:
            library_context += f"- {t.get('title')}\n"

    if not volumes_resp.data and not trailheads_resp.data:
        library_context = "No existing library. Suggest broad, engaging mystery themes."
    
    print(f"Context Length: {len(library_context)}")
    print(f"Context Preview:\n{library_context[:200]}...")

    # 3. Call LLM
    print("Calling LLM...")
    try:
        llm = get_llm_client()
        prompt = prompts.STORY_SUGGESTION_PROMPT.format(library_context=library_context)
        print("Prompt constructed.")
        
        response_json = llm.chat_completion(prompt)
        print("LLM Response received.")
        print(f"Raw Response:\n{response_json}")
        
        suggestions_data = json.loads(response_json)
        print(f"Parsed {len(suggestions_data)} suggestions.")
        for s in suggestions_data:
            print(f"- {s.get('theme')}")

    except Exception as e:
        print(f"Error during LLM call: {e}")

if __name__ == "__main__":
    test_suggestions()
