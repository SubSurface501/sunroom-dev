import logging
import json
import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

# Assuming these import paths align with your project structure
from llm.client import get_llm_client
from db.session import get_db

logger = logging.getLogger(__name__)

class MemoryObject:
    def __init__(self, 
                 content: str, 
                 importance: int, 
                 embedding: List[float], 
                 metadata: Dict = None,
                 created_at: float = None):
        self.id = str(uuid4())
        self.content = content
        self.importance = importance # 1-10
        self.embedding = embedding
        self.metadata = metadata or {}
        self.created_at = created_at or time.time()
        
        # Access time for recency decay (updated on retrieval)
        self.last_accessed_at = self.created_at

class MemoryStream:
    """
    Implements the Cognitive Memory Architecture:
    1. Ingestion with LLM-based Importance Evaluation.
    2. Dual-Store: Short-Term (RAM) vs Long-Term (Vector DB/Atoms).
    3. Retrieval with Weighted Scoring (Recency + Importance + Relevance).
    """
    
    def __init__(self, user_id: str, db=None, llm=None, universe_id: str = None):
        self.user_id = user_id
        self.db = db or get_db()
        self.llm = llm or get_llm_client()
        self.universe_id = universe_id
        
        # Short-Term Memory (The "Working Context")
        # In a real persistence layer, this might be loaded from Redis or a specialized table
        self.short_term_buffer: List[MemoryObject] = []
        
        # Weights for the Retrieval Score
        self.alpha_recency = 1.0
        self.alpha_importance = 1.0
        self.alpha_relevance = 1.0
        
        # Threshold to promote a memory to Long-Term (Atom)
        self.long_term_threshold = 7 

    def add_observation(self, text: str, metadata: Dict = None) -> MemoryObject:
        """
        The Ingestion Engine.
        1. Evaluate Importance.
        2. Generate Embedding.
        3. Store in ST-Buffer.
        4. (Optional) Persist to LT-Store if important.
        """
        # 1. Evaluate Importance (Semantic Judgment)
        importance_score = self._rate_importance(text)
        
        # 2. Generate Embedding
        embedding = self.llm.get_embedding(text)
        if not embedding:
            logger.warning("Failed to generate embedding for memory.")
            # Fallback zero-vector or handle error
            embedding = [0.0] * 768 # Matching Gemini text-embedding-004 dimension
            
        # 3. Create Memory Object
        memory = MemoryObject(
            content=text,
            importance=importance_score,
            embedding=embedding,
            metadata=metadata
        )
        
        # 4. Add to Short Term Buffer
        self.short_term_buffer.append(memory)
        
        # 5. Persist to Long Term (Atoms) if Significant
        if importance_score >= self.long_term_threshold:
            self._persist_to_long_term(memory)
            
        return memory

    def reflect(self) -> List[str]:
        """
        The 'Sleep' Cycle.
        Analyzes recent memories to synthesize new semantic concepts or rules.
        Returns a list of newly created concepts.
        """
        # 1. Gather recent significant memories (last N items)
        if not self.short_term_buffer:
            return []
            
        # Get top recent memories by importance
        recent_memories = sorted(self.short_term_buffer[-10:], key=lambda m: m.importance, reverse=True)
        memory_text = "\n".join([f"- {m.content}" for m in recent_memories])
        
        # 2. Prompt for Synthesis
        prompt = f"""
        Analyze these recent observations from an agent's life:
        {memory_text}
        
        TASK:
        Identify a generalized pattern, rule, or fact about the world that can be inferred from these specific events.
        Do not just summarize. Generalize.
        Example: "I ate a red berry and got sick" -> "Red berries are poisonous."
        
        If no clear pattern exists, return "None".
        If a pattern exists, return it as a concise statement.
        """
        
        try:
            insight = self.llm.chat_completion(prompt, json_schema=None)
            if "None" in insight or len(insight) < 5:
                return []
                
            # 3. Persist as a new CONCEPT Atom (Semantic Knowledge)
            # Note: We use type='concept' or 'rule'
            embedding = self.llm.get_embedding(insight)
            if not embedding: embedding = [0.0] * 768
            
            atom_data = {
                "user_id": self.user_id,
                "name": f"Insight: {insight[:50]}...",
                "type": "concept", 
                "metadata": {
                    "full_text": insight,
                    "source": "reflection",
                    "importance": 10 # Insights are high value
                },
                "embedding": embedding
            }
            self.db.table("Atoms").insert(atom_data).execute()
            logger.info(f"Reflection synthesized new concept: {insight}")
            return [insight]
            
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return []

    def retrieve(self, query: str, limit: int = 5) -> List[MemoryObject]:
        """
        The Retrieval Engine.
        Scores memories based on Recency, Importance, and Relevance.
        """
        query_embedding = self.llm.get_embedding(query)
        if not query_embedding:
            return []

        scored_memories = []
        
        # A. Score Short-Term Memories
        for mem in self.short_term_buffer:
            score = self._calculate_score(mem, query_embedding)
            scored_memories.append((score, mem))
            
        # B. Score Long-Term Memories (Atoms)
        # This requires a vector search against the DB, then converting results to MemoryObjects
        # For MVP, we'll implement the logic assuming an _fetch_relevant_atoms method
        long_term_candidates = self._fetch_relevant_atoms_as_memories(query_embedding, limit=limit*2)
        for mem in long_term_candidates:
            # Re-score locally to mix with ST memories accurately
            score = self._calculate_score(mem, query_embedding)
            scored_memories.append((score, mem))
            
        # C. Sort and Slice
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Update 'last_accessed' for retrieved items (Recency Boost)
        top_results = [m[1] for m in scored_memories[:limit]]
        current_time = time.time()
        for mem in top_results:
            mem.last_accessed_at = current_time
            
        return top_results

    def _rate_importance(self, text: str) -> int:
        """
        Asks LLM to rate the importance of a memory from 1-10.
        """
        prompt = f"""
        On a scale of 1 to 10, where 1 is purely mundane (e.g., "washing hands") 
        and 10 is critically important (e.g., "a break up", "finding a clue"), 
        rate the likely poignancy and information retention value of the following memory.
        
        Memory: "{text}"
        
        Return ONLY the integer.
        """
        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            score = int(''.join(filter(str.isdigit, response)))
            return max(1, min(10, score))
        except Exception as e:
            logger.error(f"Error rating importance: {e}")
            return 5 # Default neutral score

    def _calculate_score(self, memory: MemoryObject, query_embedding: List[float]) -> float:
        """
        Score = (Relevance * w) + (Importance * w) + (Recency * w)
        """
        # 1. Relevance (Cosine Similarity)
        relevance = self._cosine_similarity(memory.embedding, query_embedding)
        
        # 2. Importance (Normalized 0-1)
        importance = memory.importance / 10.0
        
        # 3. Recency (Exponential Decay)
        # Hours since last access
        hours_passed = (time.time() - memory.last_accessed_at) / 3600
        # Decay function: 0.99 ^ hours
        recency = math.pow(0.99, hours_passed)
        
        total_score = (self.alpha_relevance * relevance) + \
                      (self.alpha_importance * importance) + \
                      (self.alpha_recency * recency)
                      
        return total_score

    def _persist_to_long_term(self, memory: MemoryObject):
        """
        Saves a high-importance memory as an 'Atom' in the DB.
        This is our 'Semantic Memory' store.
        """
        try:
            # Convert embedding to string format if DB requires it, or pass raw if using pgvector client
            # The schema usually expects a specific format.
            
            atom_data = {
                "user_id": self.user_id,
                "name": f"Memory: {memory.content[:50]}...", # Truncated name
                "type": "memory", # New type to distinguish from 'concept'
                "metadata": {
                    "full_text": memory.content,
                    "importance": memory.importance,
                    "original_timestamp": memory.created_at
                },
                "embedding": memory.embedding # Supabase/pgvector handles list<float> usually
            }
            
            self.db.table("Atoms").insert(atom_data).execute()
            logger.info(f"Persisted important memory to Long Term: {memory.content[:30]}...")
            
        except Exception as e:
            logger.error(f"Error persisting memory to DB: {e}")

    def _fetch_relevant_atoms_as_memories(self, query_vector: List[float], limit: int) -> List[MemoryObject]:
        """
        Uses RPC or direct vector search to find Atoms.
        Converts them back to MemoryObjects for unified scoring.
        """
        try:
            # Assuming an RPC function 'match_atoms' exists (standard Supabase pattern)
            # or we do client-side if dataset is small (but LT is usually large).
            # For MVP, we'll try to use a hypothetical RPC call.
            
            params = {
                "query_embedding": query_vector,
                "match_threshold": 0.5,
                "match_count": limit,
                "query_user_id": self.user_id, # Updated param name to match RPC V6+
                "filter_universe_ids": [self.universe_id] if self.universe_id else None # ISOLATION FIX
            }
            # Note: This RPC function needs to exist in your DB migrations.
            # If not, this step will fail. 
            # We will catch error and return empty for now.
            res = self.db.rpc("match_atoms", params).execute()
            
            memories = []
            for record in res.data:
                # Reconstruct MemoryObject
                mem = MemoryObject(
                    content=record.get('metadata', {}).get('full_text', record.get('name')),
                    importance=record.get('metadata', {}).get('importance', 5),
                    embedding=json.loads(record['embedding']) if isinstance(record['embedding'], str) else record['embedding'],
                    metadata=record.get('metadata'),
                    created_at=record.get('created_at') # Needs parsing if string
                )
                memories.append(mem)
            return memories
            
        except Exception as e:
            # logger.warning(f"Long-term memory fetch failed (RPC missing?): {e}")
            return []

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2: return 0.0
        dot = sum(a*b for a,b in zip(v1, v2))
        norm_a = math.sqrt(sum(a*a for a in v1))
        norm_b = math.sqrt(sum(b*b for b in v2))
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot / (norm_a * norm_b)
