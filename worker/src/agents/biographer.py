import json
import logging
import os
from typing import Dict, Any
from .base import BaseAgent
from prompts import BIOGRAPHER_PROMPT_V2 # Updated import

logger = logging.getLogger(__name__)

class BiographerAgent(BaseAgent):
    """
    The Soul Builder.
    Upgraded to V2 to support "Method Acting" extraction and "Style RAG".
    """

    def run_task(self, user_id: str, source_id: str):
        logger.info(f"Building High-Fidelity Persona V2 for User {user_id} from source {source_id}...")
        
        # 1. Fetch Transcript
        # Assuming self.db is the Supabase client based on previous patterns.
        try:
            response = self.db.table("Sources").select("raw_text").eq("id", source_id).single().execute()
            transcript = response.data.get('raw_text', '')
        except Exception as e:
            logger.error(f"Failed to fetch transcript for source {source_id}: {e}")
            return

        if not transcript:
            logger.error(f"Source {source_id} has no raw_text. Skipping persona generation.")
            return

        # 2. Run The "Method Acting" Analysis
        # We limit context to avoid token overflow, but enough to catch rhythm and style.
        # Gemini 1.5 Pro has a large context, 25k chars should be a safe initial limit.
        prompt = BIOGRAPHER_PROMPT_V2.format(transcript=transcript[:25000])
        
        try:
            response_text = self.llm.chat_completion(prompt, json_schema=None)
            persona_json = self._clean_and_parse_json(response_text)
        except Exception as e:
            logger.error(f"Failed to generate or parse persona JSON from LLM: {e}. Raw response: {response_text}")
            return

        # 3. SAVE THE SOUL (The JSON)
        # Saving to the project root for the Storybook agent to access (as per plan).
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        persona_path = os.path.join(root_path, "generated_persona_v2.json")
        try:
            with open(persona_path, "w", encoding="utf-8") as f:
                json.dump(persona_json, f, indent=2)
            logger.info(f"Persona JSON saved to {persona_path}")
        except Exception as e:
            logger.error(f"Error saving persona JSON to file: {e}")
            return
            
        # 4. [NEW] BUILD THE STYLE BANK (The Vector Snippets)
        # We extract the "Few-Shot Examples" identified by the LLM 
        # and save them as a separate "Style Reference" text file for the Writer to read.
        style_bank_content = ""
        few_shots = persona_json.get('few_shot_examples', [])
        
        if few_shots:
            for example in few_shots:
                context = example.get('context', 'General')
                excerpt = example.get('excerpt', '')
                style_bank_content += f"EXAMPLE ({context}): \"{excerpt}\"\n\n"
            
            style_path = os.path.join(root_path, "style_reference.txt")
            try:
                with open(style_path, "w", encoding="utf-8") as f:
                    f.write(style_bank_content)
                logger.info(f"Style Bank saved to {style_path}")
            except Exception as e:
                logger.error(f"Error saving style bank to file: {e}")
        else:
            logger.warning("No few-shot examples extracted for style bank.")
            
        logger.info("Persona and Style Bank constructed successfully.")
        return persona_json

    def _clean_and_parse_json(self, text: str) -> Dict:
        """Helper to strip markdown code blocks if present and parse JSON safely."""
        cleaned_text = text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```", 1)[1].split("```", 1)[0]
        return json.loads(cleaned_text.strip())