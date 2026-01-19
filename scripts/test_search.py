import asyncio
import os
from dotenv import load_dotenv
import sys

# Ensure environment variables are loaded
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

# Add project root to sys.path for module discovery
sys.path.append(project_root)

from worker.src.services.search import SearchService

async def main():
    print("👁️ Initializing Search Service...")
    
    # Debugging .env loading
    print(f"DEBUG: GOOGLE_CUSTOM_SEARCH_API_KEY = {os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")[:5]}...")
    print(f"DEBUG: GOOGLE_CUSTOM_SEARCH_CX = {os.getenv("GOOGLE_CUSTOM_SEARCH_CX")}")

    search = SearchService()
    query = "The architectural history of the Panopticon"
    
    print(f"🔍 Searching for: '{query}'")
    try:
        results = await search.search_and_extract(query, num_results=1)
        
        if results:
            print(f"✅ Success! Found {len(results)} result(s).")
            print(f"--- Top Result from {results[0].get('engine', 'Unknown')} --- ")
            print(f"Title: {results[0]['title']}")
            print(f"URL: {results[0]['url']}")
            print(f"Snippet: {results[0]['text'][:200]}...")
        else:
            print("❌ Search ran, but returned no results.")
            
    except Exception as e:
        print(f"❌ Error during search: {e}")

if __name__ == "__main__":
    asyncio.run(main())
