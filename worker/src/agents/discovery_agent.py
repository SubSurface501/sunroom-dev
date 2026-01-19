import logging
import json
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from db import crud, schemas
from ..services.search import SearchService # Import SearchService

logger = logging.getLogger(__name__)

class DiscoveryAgent(BaseAgent):
    """
    The Hunter.
    Actively searches for knowledge to resolve 'Question' Atoms.
    Implements the 'Budgeted Curiosity' protocol.
    """
    
    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        self.search_service = SearchService()

    async def resolve_gap(self, atom_id: str, budget_limit: float = 0.50):
        logger.info(f"DiscoveryAgent: Attempting to resolve Gap Atom {atom_id} (Budget: ${budget_limit})")
        
        # 1. Fetch the Atom
        try:
            # Direct DB access via supabase client
            response = self.db.table("Atoms").select("*").eq("id", atom_id).single().execute()
            atom = schemas.Atom(**response.data) if response.data else None
            
            if not atom:
                logger.error("Atom not found.")
                return
                
            if atom.type != 'question' or atom.status != 'open':
                logger.info(f"Atom {atom_id} is not an open question. Skipping.")
                return
                
        except Exception as e:
            logger.error(f"Error fetching atom: {e}")
            return

        # 2. Formulate Search Queries (The "Plan")
        queries = self._plan_search(atom)
        logger.info(f"Formulated queries: {queries}")
        
        if not queries:
            logger.warning("No queries generated. Aborting.")
            return

        # 3. Execute Search (Real Service)
        logger.info(f"Executing search for: {queries[0]}...")
        
        try:
            search_results = await self.search_service.search_and_extract(queries[0])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return

        # 4. Filter & Ingest (The "Authority Filter")
        if not search_results:
            logger.warning("No search results found.")
            return

        best_result = self._select_best_source(atom, search_results)
        
        if best_result:
            logger.info(f"Selected authoritative source: {best_result['url']}")
            
            # 5. Ingest (Create Active Discovery Source)
            new_source_data = schemas.Source(
                user_id=atom.user_id,
                title=f"Discovery: {best_result['title']}",
                source_type="web_scrape", 
                source_url=best_result['url'],
                raw_text=best_result['text'], 
                metadata={"query": queries[0], "cost": 0.03, "engine": best_result.get('engine')}
            )
            
            created_source = crud.create_source(self.db, new_source_data)
            
            # 6. Resolve the Atom
            # Link resolution source and update status
            try:
                self.db.table("Atoms").update({
                    "status": "resolved",
                    "resolution_source_id": created_source.id,
                    "updated_at": "now()"
                }).eq("id", atom.id).execute()
                
                logger.info(f"Gap {atom.name} resolved by Source {created_source.id}")
                
            except Exception as e:
                logger.error(f"Failed to update atom status: {e}")

    def _select_best_source(self, atom: schemas.Atom, results: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """
        Uses LLM to select the most authoritative and relevant source from the list.
        """
        if not results: return None
        
        candidates = ""
        for i, res in enumerate(results):
            candidates += f"[{i}] {res['title']} (Source: {res['url']})\nSnippet: {res['text'][:300]}...\n\n"
            
        prompt = f"""
        I am researching to answer: "{atom.name}"
        Context: "{atom.content}"
        
        Evaluate these search results for Authority, Relevance, and Depth.
        
        {candidates}
        
        Select the index (0-{len(results)-1}) of the single best source to read.
        If none are good, return -1.
        Return strictly JSON: {{"selected_index": int, "reason": "string"}}
        """
        
        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            elif "```" in response: response = response.split("```")[1].split("```")[0]
            
            selection = json.loads(response.strip())
            idx = selection.get("selected_index", -1)
            
            if 0 <= idx < len(results):
                return results[idx]
            else:
                logger.info("Authority Filter rejected all sources.")
                return None
        except Exception as e:
            logger.error(f"Authority Filter failed: {e}. Defaulting to first result.")
            return results[0] # Fallback

    def _plan_search(self, atom: schemas.Atom) -> List[str]:
        """
        Uses LLM to generate search queries based on the gap definition.
        """
        prompt = f"""
        I have a knowledge gap: "{atom.name}"
        Context: "{atom.content}"
        
        Generate 3 Google Search queries to find authoritative academic or primary sources to answer this.
        Return strictly a JSON list of strings.
        """
        try:
            response = self.llm.chat_completion(prompt)
            # Basic cleaning
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            elif "```" in response: response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except:
            return [atom.name] # Fallback

