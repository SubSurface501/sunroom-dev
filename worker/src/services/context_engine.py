import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContextEngine:
    def __init__(self, db=None):
        self.db = db

    def get_context_from_db(self, volume_id: str, node_id: str) -> str:
        """
        Retrieves 'The Story So Far' by traversing the persisted graph in the DB.
        """
        if not self.db:
            raise ValueError("Database connection required for DB traversal.")

        try:
            # 1. Fetch Volume Graph
            vol = self.db.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
            if not vol.data:
                return "No volume found."
            
            graph = vol.data.get('graph_structure', {})
            return self.build_context_string(graph, node_id)
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return ""

    def get_context_from_memory(self, nodes: List[Dict], connections: List[Dict], current_node_id: str) -> str:
        """
        Retrieves 'The Story So Far' from an in-memory graph structure.
        """
        graph = {
            "nodes": nodes,
            "connections": connections
        }
        return self.build_context_string(graph, current_node_id)

    def build_context_string(self, graph: Dict, node_id: str) -> str:
        """
        Core logic: Backtracks from node_id to root and formats the narrative.
        """
        nodes = graph.get('nodes', [])
        connections = graph.get('connections', [])
        
        # 1. Indexing
        node_map = {n['node_id']: n for n in nodes}
        parent_map = {}
        
        for conn in connections:
            target = conn['to']
            source = conn['from']
            # In a DAG, a node might have multiple parents. 
            # For "The Story So Far", we ideally want the *primary* path or all paths.
            # For simplicity in V1, we take the first parent found (Dominant Lineage).
            if target not in parent_map:
                parent_map[target] = source
            
        # 2. Backtracking
        path = []
        curr = node_id
        
        # Safety limit for infinite loops (though it should be DAG)
        steps = 0
        while curr and steps < 50:
            if curr in node_map:
                path.append(node_map[curr])
            
            curr = parent_map.get(curr)
            steps += 1
            
        # 3. Formatting
        # Reverse to get Chronological Order (Root -> Current)
        path.reverse()
        
        if not path:
            return "No context available."

        context_str = "--- THE STORY SO FAR ---\n"
        for i, node in enumerate(path):
            title = node.get('title', 'Untitled')
            summary = node.get('summary', '')
            # We skip the very last node if it's the one we are generating FROM? 
            # No, we usually want to include the current node as the 'Tip'.
            context_str += f"{i+1}. [{title}]: {summary}\n"
            
        return context_str
