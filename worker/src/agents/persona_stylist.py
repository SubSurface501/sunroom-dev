import logging
import json
from typing import Dict, List, Optional
from .base import BaseAgent
from db import crud, schemas

logger = logging.getLogger(__name__)

class PersonaStylistAgent(BaseAgent):
    """
    Analyzes a story's context and generates a dynamic, story-specific
    persona and style guide based on the user's relevant past writings.
    """
    def run_task(self, user_id: str, volume_id: str, universe_ids: Optional[List[str]] = None) -> Dict:
        logger.info(f"Generating dynamic persona for Volume {volume_id}...")
        
        try:
            # 1. Fetch Volume and associated Nodes
            vol_res = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
            if not vol_res.data:
                logger.error(f"PersonaStylist: Could not find volume {volume_id}.")
                return self._get_default_persona("Volume not found.")

            nodes_res = self.db.table("Nodes").select("content").eq("volume_id", volume_id).execute()
            if not nodes_res.data:
                logger.warning(f"PersonaStylist: Volume {volume_id} has no nodes yet. Using root concept for style.")
                story_context = vol_res.data.get('root_concept', '')
            else:
                # 2. Aggregate all text context from the volume
                node_summaries = [node['content'].get('summary', '') for node in nodes_res.data if node.get('content')]
                story_context = vol_res.data.get('root_concept', '') + "\n" + "\n".join(node_summaries)

            if not story_context.strip():
                logger.warning(f"PersonaStylist: No text context found for volume {volume_id}.")
                return self._get_default_persona("No text context in volume.")

            # 3. Find relevant writing samples from user's history via vector search
            logger.info("Finding relevant writing samples via vector search...")
            query_embedding = self.llm.get_embedding(story_context)
            
            # Search for text-based atoms that represent the user's writing
            relevant_atoms = crud.match_atoms_by_embedding(
                self.db,
                query_embedding=query_embedding,
                match_threshold=0.75, # Higher threshold for more relevant style matching
                match_count=10,
                query_user_id=user_id,
                filter_lenses=[ # Only search for atoms that represent writing
                    schemas.AtomType.THOUGHT.value, 
                    schemas.AtomType.INSIGHT.value, 
                    schemas.AtomType.SEED_PROSE.value
                ],
                filter_universe_ids=universe_ids # New filter
            )

            if not relevant_atoms:
                logger.warning("No relevant writing samples found in user's history for this story.")
                return self._get_default_persona("No relevant writing samples found.")

            # 4. Synthesize a persona from the samples
            logger.info(f"Found {len(relevant_atoms)} relevant writing samples. Synthesizing persona...")
            
            samples_text = "\n\n---\n\n".join([atom['content'] for atom in relevant_atoms if atom.get('content')])
            
            synthesis_prompt = f"""
            You are a master literary critic. Analyze the following text samples written by an author.
            Based *only* on these samples, generate a JSON profile describing their writing style.

            The JSON object must include:
            - "name": A creative name for this specific writing style (e.g., "Pragmatic Futurist", "Poetic Technologist").
            - "epistemic_bias": A 1-sentence description of how this voice handles the unknown (e.g., 'Defaults to scientific skepticism and demands empirical evidence').
            - "voice_fingerprint": An object describing the core vocal qualities.
                - "tone": A 3-5 word description of the tone (e.g., "Analytical, hopeful, and slightly detached").
                - "rhythm": A short description of the pacing and rhythm (e.g., "Short, declarative sentences mixed with longer, complex thoughts.").
                - "vocabulary": A description of the typical word choice (e.g., "Prefers technical and precise language, avoids jargon where possible.").
            - "style_reference": A single, representative quote, 2-3 sentences long, taken directly from the samples that best exemplifies this style.

            INSTRUCTION: If writing samples are neutral, default the 'epistemic_bias' to "Scientific Skepticism" to align with the Ardent Knight theme.

            WRITING SAMPLES:
            ---
            {samples_text[:8000]}
            ---

            Output only the raw, valid JSON object.
            """

            try:
                response = self.llm.chat_completion(synthesis_prompt, json_schema=None)
                if "```json" in response: response = response.split("```json")[1].split("```")[0]
                persona = json.loads(response.strip())
                logger.info(f"Successfully synthesized dynamic persona: {persona.get('name')}")
                return persona
            except Exception as e:
                logger.error(f"Failed to synthesize persona from LLM response: {e}")
                return self._get_default_persona("LLM failed to generate valid persona JSON.")

        except Exception as e:
            logger.error(f"An unexpected error occurred in PersonaStylistAgent: {e}", exc_info=True)
            return self._get_default_persona(str(e))

    def _get_default_persona(self, reason: str) -> Dict:
        logger.warning(f"Falling back to default persona. Reason: {reason}")
        return {
            "name": "Default Narrator",
            "voice_fingerprint": {
                "tone": "Neutral, clear, and direct",
                "rhythm": "Standard sentence structure.",
                "vocabulary": "Accessible and straightforward language."
            },
            "style_reference": "The world was as it was. The facts were clear, and the path forward was logical. There was little room for embellishment.",
            "fallback_reason": reason
        }

