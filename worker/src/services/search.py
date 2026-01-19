import os
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build # Import for Google Custom Search
from googleapiclient.errors import HttpError # Import for API errors
import trafilatura # Import for web scraping
import asyncio # Import asyncio for to_thread
import re

class SearchService:
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
        self.google_cse_cx = os.getenv("GOOGLE_CUSTOM_SEARCH_CX")

        self.service: Optional[Any] = None
        if self.google_api_key and self.google_cse_cx:
            try:
                self.service = build("customsearch", "v1", developerKey=self.google_api_key, cache_discovery=False) # cache_discovery=False for debugging
                print("DEBUG: Google Custom Search client built successfully.")
            except Exception as e:
                print(f"ERROR: Failed to build Google Custom Search client: {e}")
                self.service = None
        
        if not self.service:
            print("Warning: Google Custom Search API keys or CX not configured or client build failed. SearchService will return mock data.")

    async def search_and_extract(self, query: str, num_results: int = 3, prohibitions: List[str] = None) -> List[Dict[str, Any]]:
        """
        Performs a Google Custom Search to find relevant URLs and then scrapes the text content.
        Enforces 'Amnesia Protocol' by filtering results against the current Epoch's prohibitions.
        """
        if not self.service:
            return self._mock_search(query)

        # 1. Pre-Flight Check: Is the query itself illegal?
        if prohibitions:
            for term in prohibitions:
                if re.search(r'\b' + re.escape(term.lower()) + r'\b', query.lower()):
                    print(f"BLOCKED: Query '{query}' contains prohibited term '{term}' for this Epoch.")
                    return [] # Return empty to simulate "Concept does not exist"

        results = []
        try:
            # Step 1: Search for URLs (Scout phase)
            search_response = self.service.cse().list(q=query, cx=self.google_cse_cx, num=num_results).execute()
            
            for item in search_response.get('items', []):
                # 2. Content Firewall: Check title/snippet for prohibited concepts
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                combined_text = (title + " " + snippet).lower()
                
                is_safe = True
                if prohibitions:
                    for term in prohibitions:
                        if re.search(r'\b' + re.escape(term.lower()) + r'\b', combined_text):
                            is_safe = False
                            break
                
                if not is_safe:
                    continue # Skip this result (Censorship)

                url = item.get('link')
                if url:
                    # Step 2: Scrape full text from the URL (Harvest phase)
                    full_text = await self._scrape_url_with_trafilatura(url)
                    results.append({
                        "title": title,
                        "url": url,
                        "text": full_text or snippet, # Use full_text if available, else snippet
                        "author": "Unknown", # Google CSE doesn't provide author directly
                        "engine": "google_cse"
                    })
        except HttpError as e:
            print(f"ERROR during Google Custom Search API call (HttpError): {e.resp.status} - {e.content}")
            return self._mock_search(query)
        except Exception as e:
            print(f"ERROR during Google Custom Search (General Exception): {e}")
            # Fallback to mock search on error
            return self._mock_search(query)
            
        return results

    async def _scrape_url_with_trafilatura(self, url: str) -> str | None:
        """
        Scrapes the given URL using trafilatura and returns clean text.
        """
        try:
            # trafilatura.fetch_url can be blocking, so run in a separate thread/process if not async-native
            # httpx is async, trafilatura.fetch_url uses requests by default which is sync.
            # For simple script, asyncio.to_thread works. For heavy load, a ThreadPoolExecutor or process.
            # Assuming within an async context where to_thread is acceptable for I/O bound tasks.
            downloaded_html = await asyncio.to_thread(trafilatura.fetch_url, url)
            if downloaded_html:
                text = trafilatura.extract(downloaded_html, favor_recall=True, include_comments=False, include_images=False, include_formatting=False)
                return text
        except Exception as e:
            print(f"Error scraping URL {url} with trafilatura: {e}")
        return None

    def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Returns varied mock data to simulate a real search engine response.
        """
        return [
            {
                "title": f"Understanding {query}: A Comprehensive Overview",
                "url": "https://example.edu/comprehensive-guide",
                "text": f"This article provides a deep dive into {query}, covering its history, core principles, and modern applications. Experts agree that {query} is a pivotal concept in its field.",
                "author": "Dr. A. Simulation",
                "engine": "mock"
            },
            {
                "title": f"Recent Developments in {query}",
                "url": "https://tech-news.example.com/latest-updates",
                "text": f"New findings have challenged traditional views on {query}. This report analyzes the latest data from 2024 and suggests a paradigm shift.",
                "author": "Tech Staff",
                "engine": "mock"
            },
            {
                "title": f"Why {query} Matters",
                "url": "https://blog.opinionated.com/why-it-matters",
                "text": f"An opinion piece arguing that {query} is often misunderstood. The author suggests a new framework for interpreting its impact on society.",
                "author": "J. Doe",
                "engine": "mock"
            }
        ]