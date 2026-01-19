import logging
import json
from collections import Counter
from .base import BaseAgent
from db import crud, schemas

logger = logging.getLogger(__name__)

class PersonaBuilderAgent(BaseAgent):
    """
    The Cartographer.
    Constructs the Persona Profile (The Stable Self).
    Implements MirrorMind Sec 2.2.3.
    """

    def run_task(self, user_id: str):
        logger.info(f"🗺️ Persona Builder started for User {user_id}")
        
        # 0. Fetch Existing Profile to preserve manual overrides (Blacklist)
        existing_profile = crud.get_persona_profile(self.db, user_id)
        ignored_concepts = []
        if existing_profile and existing_profile.stylistic_attributes:
            ignored_concepts = existing_profile.stylistic_attributes.get('ignored_concepts', [])

        # 1. Stage I: Graph Extraction (Core Concepts)
        core_concepts = self._extract_core_concepts(user_id)
        
        # Apply Blacklist
        if ignored_concepts:
            original_count = len(core_concepts)
            core_concepts = [c for c in core_concepts if c['name'] not in ignored_concepts]
            if len(core_concepts) < original_count:
                logger.info(f"🛡️ Filtered {original_count - len(core_concepts)} concepts based on user blacklist.")
        
        # 2. Stage II: Attribute Extraction (Stylistic Voice)
        attributes = self._extract_stylistic_attributes(user_id)
        
        # Preserve the blacklist in the new attributes
        if ignored_concepts:
            attributes['ignored_concepts'] = ignored_concepts
        
        # 3. Stage III: Prompt Caching
        system_prompt = self._construct_system_prompt(core_concepts, attributes)
        
        # 4. Store
        profile = schemas.PersonaProfile(
            user_id=user_id,
            core_concepts=core_concepts,
            stylistic_attributes=attributes,
            system_prompt_cache=system_prompt
        )
        crud.upsert_persona_profile(self.db, profile)
        logger.info(f"Persona Profile updated for {user_id}")

    def _extract_core_concepts(self, user_id: str) -> list:
        """
        Identifies 'Hub Concepts' by analyzing Atom frequency and linkages.
        For MVP, we count occurrences of Atom names in the AtomEdges table (if available) 
        or just frequency of Atom names if we don't have a dense edge graph yet.
        """
        # Fetch all atoms (concept type)
        # In a real graph, we'd do PageRank on AtomEdges. 
        # For MVP, we'll assume frequent indexing of the same concept name implies centrality.
        # Or better: Fetch atoms that are targets of many edges.
        
        try:
            # Query edges to find most connected atoms
            res = self.db.table("AtomEdges").select("target_atom_id").eq("user_id", user_id).execute()
            if not res.data:
                # Fallback: Just get most recent atoms
                atoms = crud.get_atoms_for_user(self.db, user_id)
                return [{"name": a.name, "weight": 1.0} for a in atoms[:10]]

            target_counts = Counter([r['target_atom_id'] for r in res.data])
            top_ids = [id for id, count in target_counts.most_common(10)]
            
            # Fetch names
            atoms_res = self.db.table("Atoms").select("name").in_("id", top_ids).execute()
            
            concepts = [{"name": a['name'], "weight": target_counts.get(a.get('id', ''), 1)} for a in atoms_res.data]
            return concepts

        except Exception as e:
            logger.warning(f"Graph extraction failed: {e}. Using fallback.")
            return []

    def _extract_stylistic_attributes(self, user_id: str) -> dict:
        """
        Samples recent text to determine voice.
        """
        # Get recent atom content
        atoms = crud.get_atoms_for_user(self.db, user_id) # Should paginate/limit
        if not atoms:
            return {}
            
        # Sample last 10 atoms
        sample_text = "\n".join([f"- {a.content}" for a in atoms[-10:]])
        
        prompt = f"""
        Analyze the following samples of the user's thought process.
        Determine their Stylistic Attributes.
        
        Samples:
        {sample_text[:3000]}
        
        Output JSON:
        {{
            "tone": "...", 
            "reasoning_pattern": "inductive/deductive/lateral",
            "vocabulary_complexity": "high/medium/low",
            "keywords": ["...", "..."]
        }}
        """
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            # Clean
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            return json.loads(resp.strip())
        except Exception as e:
            logger.error(f"Attribute extraction failed: {e}")
            return {}

    def _construct_system_prompt(self, concepts: list, attributes: dict) -> str:
        """
        Serializes the persona into a prompt string.
        """
        concept_str = ", ".join([c['name'] for c in concepts])
        
        return f"""
        You are simulating a specific researcher.
        Core Concepts: {concept_str}
        Tone: {attributes.get('tone', 'Neutral')}
        Reasoning: {attributes.get('reasoning_pattern', 'Analytical')}
        Vocabulary: {attributes.get('vocabulary_complexity', 'High')}
        
        Think as this person would. Ground all new ideas in these Core Concepts.
        """
