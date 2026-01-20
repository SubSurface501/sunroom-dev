import logging
import json
import os
import time
import sys
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from worker.src.agents.base import BaseAgent
from prompts import STORY_OUTLINER_PROMPT, STORY_PAGE_WRITER_PROMPT_V2 # Updated import
from db import crud, schemas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorybookAgent(BaseAgent):
    """
    The Writer V2.
    Fixes 'Caricature Loop' via Dynamic Ban Lists.
    Fixes 'Voice' via Style RAG (Retrieval-Augmented Generation).
    """

    def run_task(self, user_id: str, trailhead_id: str = None, source_id: str = None, target_length: int = 12, visual_style: str = "Graphic Novel"):
        logger.info(f"Starting Saga Generation V2 for user {user_id}. Target Length: {target_length} pages.")

        # 1. Load Persona Context V2 (The "Soul")
        context_data = self._load_persona_context()
        persona = context_data.get('rules', {})
        style_examples = context_data.get('examples', "No style examples found.")
        
        persona_name = persona.get('meta', {}).get('name', 'The Narrator')
        bio_markers = ", ".join(persona.get('cognitive_architecture', {}).get('worldview', []))
        core_beliefs = str(persona.get('cognitive_architecture', {}).get('worldview', []))
        
        # Extract phrases and their triggers/weights for dynamic constraints
        signature_phrases_config = persona.get('lexicon_constraints', {}).get('catchphrases', [])
        signature_phrases = [p['phrase'] for p in signature_phrases_config] # Just the phrase string
        voice_tone = persona.get('voice_fingerprint', {}).get('tone', 'Scholarly, Conversational, Reverent') # Fallback if not in v2 persona

        # 2. Load Context (The "Brain")
        lesson_context, trailhead_title, ground_truth_text = self._get_lesson_context(user_id, trailhead_id, source_id)
        if not lesson_context:
            logger.error("Failed to retrieve lesson context.")
            return

        # 3. Load Cast (The "Library")
        characters_str, artifacts_str = self._get_cast_and_artifacts(user_id)

        # 4. PHASE 1: The Outline (The "Beat Sheet")
        logger.info("Phase 1: Drafting Outline...")
        
        q1 = int(target_length * 0.25)
        q2 = int(target_length * 0.5)
        q3 = int(target_length * 0.75)

        outline_prompt = STORY_OUTLINER_PROMPT.format(
            page_count=target_length,
            lesson_context=lesson_context,
            characters=characters_str,
            artifacts=artifacts_str,
            q1=q1, q2=q2, q3=q3
        )

        outline_response = self.llm.chat_completion(outline_prompt, json_schema=None)
        try:
            beat_sheet = self._clean_and_parse_json(outline_response) # Use the new robust parser
            if not isinstance(beat_sheet, list):
                raise ValueError("Outline is not a list")
            logger.info(f"Outline generated with {len(beat_sheet)} beats.")
        except Exception as e:
            logger.error(f"Failed to generate or parse outline: {e}. Raw response: {outline_response}")
            return

        # 5. PHASE 2: The Writer (The "Page Loop")
        logger.info("Phase 2: Writing Pages...")
        pages = [] # This will store the full page manifests as they are created
        previous_context_text = "The story begins."

        for i, beat in enumerate(beat_sheet):
            page_num = i + 1
            logger.info(f"Writing Page {page_num}/{len(beat_sheet)}...")

            # --- THE FIX: The "Caricature Loop" Detector & Dynamic Constraints ---
            dynamic_constraints = []
            if len(pages) > 0: # Only check if there are previous pages
                # Look at the narrative text of the last N pages (e.g., 3 pages) for repetition
                recent_history_texts = [p.get('narrative_text', '') for p in pages[-min(len(pages), 3):]]
                recent_history_combined = " ".join(recent_history_texts)
                
                for phrase_config in signature_phrases_config:
                    phrase = phrase_config['phrase']
                    if phrase in recent_history_combined:
                        # Create a constraint if the phrase was recently used.
                        # We use the 'trigger' if available, otherwise a generic ban.
                        trigger_desc = phrase_config.get('trigger', f"Do not use the phrase '{phrase}' if it has been used recently.")
                        dynamic_constraints.append(f"CONSTRAINT: Avoid the phrase '{phrase}' on this page, as it was recently used. Trigger: {trigger_desc}")
            
            constraint_str = " ".join(dynamic_constraints) if dynamic_constraints else "None. No recent phrase repetitions detected." # Ensure it's not empty for the prompt
            # ------------------------------------------------------------------------------------------------------

            # Construct Prompt with Style RAG + Dynamic Constraints + Ground Truth
            page_prompt = STORY_PAGE_WRITER_PROMPT_V2.format(
                persona_name=persona_name,
                bio_markers=bio_markers,
                style_examples=style_examples, # <--- INJECTED REAL VOICE EXAMPLES
                ground_truth_text=ground_truth_text, # <--- INJECTED GROUND TRUTH
                current_page_num=page_num,
                total_pages=len(beat_sheet),
                page_summary=beat,
                previous_page_context=previous_context_text,
                core_beliefs=core_beliefs, # Pass as string
                signature_phrases=", ".join(signature_phrases), # Pass all phrases for reference, but ban handles frequency
                voice_tone=voice_tone,
                dynamic_constraints=constraint_str # <--- INJECTED DYNAMIC BAN LIST
            )

            try:
                page_response = self.llm.chat_completion(page_prompt, json_schema=None)
                page_data = self._clean_and_parse_json(page_response)
                
                if not isinstance(page_data, dict):
                    logger.error(f"Unexpected data type for page {page_num}: {type(page_data)}. Content: {page_data}")
                    continue

                page_data['page_number'] = page_num
                page_data['beat_summary'] = beat
                pages.append(page_data)

                # Update Context for next loop (The "Memory")
                previous_context_text = f"Page {page_num} ended with: {page_data.get('narrative_text', '')[-200:]}"
                
                time.sleep(1) # Brief pause to be kind to the API

            except Exception as e:
                logger.error(f"Error writing page {page_num}: {e}. Raw response: {page_response}")
                continue

        # 6. Save Output
        # Fetch existing content to preserve 'research_dossier' and 'core_insight'
        existing_content = {}
        if trailhead_id:
            try:
                res = self.db.table("Trailheads").select("content").eq("id", trailhead_id).single().execute()
                if res.data:
                    existing_content = res.data.get('content') or {}
            except Exception as e:
                logger.warning(f"Could not fetch existing content to preserve: {e}")

        manifest = {
            "project_title": f"Saga: {trailhead_title}",
            "theme": lesson_context[:100], # Keep theme concise
            "style": visual_style,
            "narrator_voice_check": f"Narrated by {persona_name}, with dynamic phrase modulation.", # Updated check
            "pages": pages,
            # Preserve critical V3 keys
            "research_dossier": existing_content.get("research_dossier", []),
            "core_insight": existing_content.get("core_insight", "")
        }

        try:
            # Use crud to update or create trailhead. If trailhead_id is provided, it's an update.
            if trailhead_id:
                 self.db.table("Trailheads").update({"content": manifest}).eq("id", trailhead_id).execute()
                 logger.info(f"Updated existing Trailhead {trailhead_id} with new Saga V2 manifest.")
            else:
                crud.create_trailhead(self.db, schemas.TrailheadCreate(
                    user_id=user_id,
                    title=f"Saga: {trailhead_title}",
                    insight="A multi-page saga narrative with enhanced persona and visual consistency.",
                    suggested_topic=f"Saga: {trailhead_title}", # Populate required field
                    type="storybook_manifest",
                    content=manifest
                ))
                logger.info("New Saga V2 generation complete.")
            return manifest
        except Exception as e:
            logger.error(f"Failed to save Saga V2: {e}")
            return None

    # --- Helpers ---

    def _get_lesson_context(self, user_id, trailhead_id, source_id):
        # Existing logic for getting lesson context...
        lesson_context = ""
        title = "Untitled"
        ground_truth_text = "No specific ground truth constraints."

        if trailhead_id:
            try:
                response = self.db.table("Trailheads").select("*").eq("id", trailhead_id).eq("user_id", user_id).single().execute()
                trailhead = response.data
                if trailhead:
                    title = trailhead.get('title', 'Untitled')
                    content = trailhead.get('content') or {}
                    lesson_context = f"Title: {title}\nInsight: {trailhead.get('insight')}\nContext: {content.get('core_insight', '')}"
                    
                    # Extract Ground Truth from Dossier
                    dossier = content.get('research_dossier', [])
                    if dossier:
                        ground_truth_text = "\n".join([f"- {item['name']}: {item['definition']}" for item in dossier])

            except Exception as e:
                logger.error(f"Error fetching trailhead: {e}")
                return None, None, None
                
        elif source_id:
            # This path needs full implementation if used for direct source to saga.
            # For now, it's primarily trailhead-driven.
            logger.warning("Direct source processing for Saga not fully implemented.")
            return None, None, None
        
        if not lesson_context:
            logger.error("No context found for lesson generation.")
            return None, None, None
        return lesson_context, title, ground_truth_text

    def _get_cast_and_artifacts(self, user_id):
        try:
            # Select metadata which contains the description
            person_atoms = self.db.table("Atoms").select("name", "metadata").eq("user_id", user_id).eq("type", "person").limit(5).execute().data
            book_atoms = self.db.table("Atoms").select("name", "metadata").eq("user_id", user_id).eq("type", "book").limit(5).execute().data
        except Exception as e:
            logger.error(f"Error fetching atoms for cast: {e}")
            person_atoms = []
            book_atoms = []
            
        # Extract description from metadata, defaulting to 'No description'
        c_str = ", ".join([f"{p['name']} ({p.get('metadata', {}).get('description', 'No description')})" for p in person_atoms]) if person_atoms else "A lone seeker"
        a_str = ", ".join([f"{b['name']} ({b.get('metadata', {}).get('description', 'No description')})" for b in book_atoms]) if book_atoms else "Ancient texts"
        return c_str, a_str

    def _clean_and_parse_json(self, text: str) -> Dict:
        """Helper to strip markdown code blocks if present and parse JSON safely."""
        cleaned_text = text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```", 1)[1].split("```", 1)[0]
        return json.loads(cleaned_text.strip())

    def _load_persona_context(self) -> Dict[str, Any]:
        """
        Loads the structured persona JSON (V2) and the text-based Style RAG examples.
        """
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        
        # Load structured persona rules
        persona_json_path = os.path.join(root_path, "generated_persona_v2.json")
        rules = {}
        if os.path.exists(persona_json_path):
            try:
                with open(persona_json_path, "r", encoding="utf-8") as f: 
                    rules = json.load(f)
            except Exception as e:
                logger.error(f"Error loading generated_persona_v2.json: {e}")
        else:
            logger.warning(f"generated_persona_v2.json not found at {persona_json_path}. Using empty persona rules.")

        # Load Style RAG examples
        style_ref_path = os.path.join(root_path, "style_reference.txt")
        examples = "No style examples found." # Default message if file not found
        if os.path.exists(style_ref_path):
            try:
                with open(style_ref_path, "r", encoding="utf-8") as f:
                    examples = f.read()
            except Exception as e:
                logger.error(f"Error loading style_reference.txt: {e}")
        else:
            logger.warning(f"style_reference.txt not found at {style_ref_path}. Using default style examples.")
            
        return {"rules": rules, "examples": examples}
