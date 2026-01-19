import logging
import json
from typing import List, Dict
from .base import BaseAgent

logger = logging.getLogger(__name__)

class ResearcherAgent(BaseAgent):
    """
    The Hydrator.
    Implements "Semantic Locking" and "Context Inheritance".
    Ensures that every node has a specific set of "Ground Truth" atoms attached to it
    BEFORE the writer starts working.
    """

    def run_task(self, volume_id: str, user_id: str): # Add user_id param
        logger.info(f"Hydrating Volume {volume_id}...")
        
        # 1. Fetch Volume & Graph
        try:
            volume_response = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
            volume = volume_response.data
            if not volume:
                logger.error("Volume not found.")
                return
        except Exception as e:
            logger.error(f"Error fetching volume: {e}")
            return
        
        # REMOVED: volume_user_id extraction (now passed as arg)

        graph = volume.get('graph_structure', {})
        
        # 2. Fetch All Nodes for this Volume
        try:
            nodes_response = self.db.table("Nodes").select("*").eq("volume_id", volume_id).execute()
            nodes = nodes_response.data
        except Exception as e:
            logger.error(f"Error fetching nodes: {e}")
            return

        # Map real UUID -> Node Data for easy lookup
        node_lookup = {n['id']: n for n in nodes}
        # Map Blueprint ID -> Real UUID (from the Architect's map)
        blueprint_map = graph.get('node_id_map', {})
        
        # We need to process in topological order (parents first) to handle inheritance.
        # For simplicity in this MVP, we'll just do a robust pass since inheritance is 1-level deep usually in blueprints.
        # Ideally, we traverse the graph. Here, we'll iterate.
        
        for node in nodes:
            logger.debug(f"Node object in researcher loop: {node}") # Added debug log
            logger.info(f"Researching Node: {node.get('title')}")
            content = node.get('content', {})
            summary = content.get('summary', '')
            # user_id = node['user_id'] # Removed as user_id is from volume
            
            # A. IDENTIFY CONCEPTS (Simple Keyword Extraction via LLM)
            queries = self._identify_concepts_llm(summary)
            
            # B. RETRIEVE ATOMS (DB Lookup - The "Local Dossier")
            local_dossier = self._build_dossier(queries, user_id) # Use the passed user_id here
            
            # C. INHERITANCE (Plan 2 Logic)
            # Find parent node ID from graph.
            # 1. Get Blueprint ID of this node
            blueprint_id = content.get('blueprint_id')
            unified_parent_dossier = [] # Initialize here to ensure it always exists

            if blueprint_id:
                # 2. Find connection in graph where 'to' == blueprint_id
                connections = graph.get('connections', [])
                parent_blueprint_ids = []
                for conn in connections:
                    if conn.get('to') == blueprint_id:
                        parent_blueprint_ids.append(conn.get('from'))
                
                # 3. If parents found, get their Real UUIDs and fetch their dossiers
                for p_blueprint_id in parent_blueprint_ids:
                    parent_real_id = blueprint_map.get(p_blueprint_id)
                    if parent_real_id and parent_real_id in node_lookup:
                        parent_node = node_lookup[parent_real_id]
                        # We assume parent is processed or we fetch what it has. 
                        # In a real BFS, parent would be done. Here we just check if it has data.
                        current_parent_dossier = parent_node.get('content', {}).get('research_dossier', [])
                        unified_parent_dossier = self._merge_dossiers(unified_parent_dossier, current_parent_dossier)

            # Merge: Child definitions override Parent definitions if conflict (by Name)
            final_dossier = self._merge_dossiers(unified_parent_dossier, local_dossier)
            
            # D. SAVE
            content['research_dossier'] = final_dossier
            content['research_status'] = 'complete'
            
            try:
                self.db.table("Nodes").update({"content": content}).eq("id", node['id']).execute()
            except Exception as e:
                logger.error(f"Error saving dossier for node {node['id']}: {e}")
                
        # Update Volume Status
        try:
            self.db.table("StoryVolumes").update({"status": "hydrated"}).eq("id", volume_id).execute()
            logger.info(f"Volume {volume_id} hydration complete.")
        except Exception as e:
            logger.error(f"Error updating volume status: {e}")

    def _identify_concepts_llm(self, summary: str) -> List[str]:
        """
        Asks LLM to pick 3-5 key academic/esoteric terms from the summary to lookup.
        """
        prompt = f"""
        Analyze this plot summary: "{summary}"
        Identify 3-5 specific esoteric, historical, or academic concepts that define the "Ground Truth" of this scene.
        Return ONLY a JSON list of strings.
        Example: ["Golem", "Sefer Yetzirah", "Prague"]
        """
        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            # Basic cleaning
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except:
            return []

    def _build_dossier(self, queries: List[str], user_id: str) -> List[Dict]:
        """
        Searches Atoms table for each query.
        """
        dossier = []
        for q in queries:
            try:
                # ILIKE search
                res = self.db.table("Atoms").select("name, metadata").eq("user_id", user_id).ilike("name", f"%{q}%").limit(1).execute()
                if res.data:
                    atom = res.data[0]
                    desc = atom.get('metadata', {}).get('description') or "No definition found."
                    dossier.append({"name": atom['name'], "definition": desc})
            except Exception as e:
                continue
        return dossier

    def _merge_dossiers(self, parent: List[Dict], child: List[Dict]) -> List[Dict]:
        """
        Merges two lists of dicts. Child overrides parent if 'name' matches.
        """
        merged = {item['name']: item for item in parent}
        for item in child:
            merged[item['name']] = item # Override/Add
        return list(merged.values())
