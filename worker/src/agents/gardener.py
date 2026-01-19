import logging
import numpy as np
import json
from llm.client import get_llm_client

logger = logging.getLogger(__name__)

class GardenerAgent:
    def __init__(self, db):
        self.db = db
        self.llm = get_llm_client()

    def find_structural_holes(self, volume_id: str):
        """
        Scans the volume for 'Creative Adjacencies'—atoms that are 
        semantically related (Sim 0.5-0.7) but unconnected.
        """
        logger.info(f"🌿 Gardener scanning volume {volume_id} for structural holes...")
        
        # 1. Fetch all atoms with embeddings
        # Note: We limit to a reasonable number to prevent O(N^2) explosion in this MVP logic
        response = self.db.table("Atoms").select("id, content, embedding").eq("volume_id", volume_id).limit(200).execute()
        
        # Parse embeddings
        atoms = []
        for a in response.data:
            if not a.get('embedding'): continue
            
            emb = a['embedding']
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except:
                    continue
            atoms.append({**a, 'embedding': emb})
        
        if len(atoms) < 2:
            return []

        suggestions = []
        
        # 2. Matrix calculation (O(N^2))
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                atom_a = atoms[i]
                atom_b = atoms[j]
                
                vec_a = np.array(atom_a['embedding'])
                vec_b = np.array(atom_b['embedding'])
                
                norm_a = np.linalg.norm(vec_a)
                norm_b = np.linalg.norm(vec_b)
                
                if norm_a == 0 or norm_b == 0:
                    sim = 0
                else:
                    sim = np.dot(vec_a, vec_b) / (norm_a * norm_b)
                
                # The "Creative Sweet Spot": 0.5 to 0.75
                # Too high (>0.8) = Redundant (Synonyms)
                # Too low (<0.4) = Random noise
                if 0.5 < sim < 0.75:
                    # Check if connection already exists (Mock check - simply returning pair now)
                    # In a full graph DB, we'd check edge table.
                    suggestions.append({
                        "atom_a": atom_a,
                        "atom_b": atom_b,
                        "score": float(sim),
                        "reason": "Topological adjacency detected."
                    })
        
        # Return top 3 most interesting disconnects
        return sorted(suggestions, key=lambda x: x['score'], reverse=True)[:3]

    def propose_bridge(self, atom_a, atom_b):
        """
        Generates a hypothesis linking two disparate thoughts.
        """
        prompt = f"""
        I found two disconnected thoughts in the user's mind:
        1. "{atom_a['content']}"
        2. "{atom_b['content']}"
        
        Task: Act as a 'Serendipity Engine'.
        Propose a novel hypothesis or insight that bridges these two concepts.
        Explain WHY they are connected.
        """
        bridge_thought = self.llm.chat_completion(prompt)
        return bridge_thought
