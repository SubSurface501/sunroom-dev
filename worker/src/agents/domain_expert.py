import logging
import json
import uuid
import requests
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from db import crud, schemas

logger = logging.getLogger(__name__)

class DomainExpertAgent(BaseAgent):
    """
    The MirrorMind 'Domain Level' Agent.
    Responsible for:
    1. Concept Search (Mapping query to Concept Graph)
    2. Graph Traversal (Finding paths between concepts)
    3. Feasibility Checking (Grounding ideas in existing edges)
    """

    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)

    def search_concepts(self, query: str, user_id: str, project_id: str = None, limit: int = 5, universe_ids: List[str] = None) -> List[Dict]:
        """
        Finds 'Concept' atoms relevant to the query.
        """
        embedding = self.llm.get_embedding(query)
        if not embedding:
            return []
            
        # Use existing match_atoms (filtered by type='concept')
        matches = crud.match_atoms_by_embedding(
            self.db, 
            embedding, 
            match_threshold=0.6, 
            match_count=limit, 
            query_user_id=user_id,
            query_project_id=project_id,
            filter_universe_ids=universe_ids # ISOLATION FIX
            # We assume match_atoms can filter by type via metadata or we filter post-fetch
            # For now, we'll filter manually if the RPC doesn't support 'type' arg explicitly
        )
        
        # Filter for only 'concept' type if the RPC mixed types
        concepts = [m for m in matches if m.get('type') == 'concept']
        return concepts

    def find_path(self, start_concept_id: str, end_concept_id: str, max_depth: int = 3) -> List[Dict]:
        """
        Finds a narrative path (chain of atoms) between two concepts using BFS.
        Returns a list of Atoms representing the path: [Start, A, B, End]
        """
        logger.info(f"Finding path from {start_concept_id} to {end_concept_id} (Max Depth: {max_depth})")
        
        queue = [[start_concept_id]]
        visited = {start_concept_id}
        
        # This is a naive BFS implementation. Ideally, this logic should be in a Postgres Recursive CTE.
        # But for the Python agent, we'll do iterative fetching.
        
        while queue:
            path = queue.pop(0)
            current_id = path[-1]
            
            if current_id == end_concept_id:
                return self._fetch_atoms_by_ids(path)
            
            if len(path) > max_depth:
                continue
                
            # Get neighbors (Targets where current is Source)
            # We might also want bidirectional, but let's stick to directed "Flow" for now
            neighbors = self._get_neighbors(current_id)
            
            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    new_path = list(path)
                    new_path.append(neighbor_id)
                    queue.append(new_path)
                    
        return [] # No path found

    def find_domain_path(self, concept_A_name: str, concept_B_name: str, domain: str = "General Science") -> List[Dict]:
        """
        MirrorMind Wormhole Logic.
        Uses the LLM (Simulating OpenAlex) to find a conceptual path between two ideas *outside* the user's graph.
        Returns a list of dictionaries [{'name': '...', 'definition': '...'}, ...]
        """
        logger.info(f"🌌 wormhole search: {concept_A_name} -> {concept_B_name} in {domain}")
        
        prompt = f"""
        You are an expert in {domain}.
        Task: Identify the conceptual bridge between "{concept_A_name}" and "{concept_B_name}".
        
        Find a chain of 1-3 intermediate concepts that logically link them.
        Strictly follow valid scientific or philosophical relationships.
        
        Output JSON list of objects: [{{ "name": "Concept Name", "definition": "Brief definition", "relation_to_prev": "How it links" }}]
        """
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            
            path_data = json.loads(resp.strip())
            return path_data
        except Exception as e:
            logger.error(f"Domain path search failed: {e}")
            return []

    def search_external_concepts(self, query: str, domain: str = "General") -> List[Dict]:
        """
        Searches OpenAlex for real scientific concepts/works.
        Replaces previous LLM simulation.
        """
        logger.info(f"🔎 Querying OpenAlex for: {query}")
        try:
            # Search for 'works' (papers) related to the query
            url = f"https://api.openalex.org/works?search={query}&per-page=5"
            # Polite pool: It's good practice to send an email in the User-Agent or params
            response = requests.get(url, headers={"User-Agent": "mailto:dev@sunroom.local"}, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for work in data.get('results', []):
                title = work.get('title')
                # Get concepts from the work
                concepts = [c['display_name'] for c in work.get('concepts', [])[:3]]
                summary_text = f"Real scientific work. Key Concepts: {', '.join(concepts)}."
                
                # We format it to match the expected return structure
                results.append({
                    "name": title,
                    "definition": summary_text,
                    "field": "OpenAlex Science",
                    "source": "OpenAlex",
                    "url": work.get('doi') or work.get('id'),
                    "confidence": 1.0 # Real paper
                })
            
            return results
            
        except Exception as e:
            logger.error(f"OpenAlex lookup failed: {e}")
            return []

    def synthesize_community_patterns(self, atoms: List[Dict], topic: str) -> str:
        """
        PersonaAgent Logic: Transforms raw community atoms into 'Global Interaction Patterns'.
        Instead of a flat list, we return a structured summary of the Community's consensus.
        """
        if not atoms:
            return "No community data available to form a pattern."

        # Prepare input context
        atom_list_text = "\n".join([f"- {a['name']}: {a['content'][:200]}..." for a in atoms])

        prompt = f"""
        You are the Collective Consciousness Analyst.
        Task: Analyze the following 'Community Atoms' related to the topic "{topic}".
        
        Input Data (Raw Atoms):
        {atom_list_text}
        
        Identify the 'Global Interaction Patterns' and Consensus. 
        Do not just list the atoms. Synthesize them into a structural summary.
        
        1. **Dominant Narrative:** What is the most common perspective or theme in this group?
        2. **Blind Spots/Outliers:** Is there a minority view?
        3. **Corrective Signal:** How does this community data constrain or guide new ideas?
        
        Output a concise summary string (approx 100 words) formatted as:
        "**Community Consensus:** ... **Outliers:** ... **Correction:** ..."
        """
        
        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            return response.strip()
        except Exception as e:
            logger.error(f"Community pattern synthesis failed: {e}")
            return "Community patterns could not be synthesized."

    def check_feasibility(self, proposition: str, context_atoms: List[Dict], community_pattern: str = None) -> float:
        """
        Objective Feasibility Score (Beta).
        Checks if the 'proposition' is supported by:
        1. Specific Evidence (User Graph / Anchor Atoms)
        2. Community Consensus (Collective Manifold)
        """
        # 1. Convert context atoms into a text representation of the graph
        graph_text = "Specific Evidence (User/Domain Atoms):\n"
        for atom in context_atoms:
            # Fetch edges for this atom
            edges = self._get_edges_full(atom['id']) 
            for edge in edges:
                 graph_text += f"- {atom['name']} {edge['relationship_type']} {edge['target_name']}\n"
        
        # 2. Add Community Pattern if available
        community_text = ""
        if community_pattern:
            community_text = f"\nCommunity Consensus & Constraints:\n{community_pattern}\n"

        # 3. Ask LLM to verify
        prompt = f"""
        You are the Scientific Feasibility Judge. 
        Proposition: "{proposition}"
        
        {graph_text}
        {community_text}
        
        Task: Determine if the Proposition is feasible.
        - It must NOT contradict the 'Community Consensus' (Validity Constraint).
        - It should ideally be supported by 'Specific Evidence' (Grounding).
        
        Scoring (0.0 to 1.0):
        - 1.0: Supported by Evidence AND Aligns with Consensus.
        - 0.8: Plausible/Transitive support, Aligns with Consensus.
        - 0.5: Neutral/Novel, but does not contradict Consensus.
        - 0.2: Weak support, minor tension with Consensus.
        - 0.0: Explicitly contradicts Evidence or Community Consensus.
        
        Output JSON: {{ "score": float, "reason": "..." }}
        """
        
        response = self.llm.chat_completion(prompt, json_schema=None)
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())
            return float(data.get("score", 0.5))
        except:
            return 0.5

    def _get_neighbors(self, atom_id: str) -> List[str]:
        """Fetch target_atom_ids where source = atom_id"""
        res = self.db.table("AtomEdges").select("target_atom_id").eq("source_atom_id", atom_id).execute()
        return [r['target_atom_id'] for r in res.data]

    def _get_edges_full(self, atom_id: str) -> List[Dict]:
        """Fetch edges with target names for context building"""
        # This requires a join, which Supabase-py might not do easily without an RPC.
        # We'll do two queries for MVP: Get Edges -> Get Target Atoms
        edges_res = self.db.table("AtomEdges").select("*").eq("source_atom_id", atom_id).execute()
        edges = edges_res.data
        
        if not edges: return []
        
        target_ids = [e['target_atom_id'] for e in edges]
        atoms_res = self.db.table("Atoms").select("id, name").in_("id", target_ids).execute()
        atom_map = {a['id']: a['name'] for a in atoms_res.data}
        
        enriched_edges = []
        for e in edges:
            e['target_name'] = atom_map.get(e['target_atom_id'], "Unknown")
            enriched_edges.append(e)
            
        return enriched_edges

    def _fetch_atoms_by_ids(self, atom_ids: List[str]) -> List[Dict]:
        if not atom_ids: return []
        res = self.db.table("Atoms").select("*").in_("id", atom_ids).execute()
        # Sort by input order
        atom_map = {a['id']: a for a in res.data}
        return [atom_map.get(aid) for aid in atom_ids if aid in atom_map]
