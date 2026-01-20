import json
import logging
import os
from typing import Dict, List, Any
from .base import BaseAgent
from prompts import SCENE_VISUALIZER_PROMPT

logger = logging.getLogger(__name__)

class DirectorAgent(BaseAgent):
    """
    The Director of Photography.
    Responsible for the "Graph of Thoughts" translation from Text -> Visual Spec.
    Prevents 'Visual Drift' by enforcing Immutable Asset Strings and a Style Anchor.
    """

    # The Style Anchor prevents the model from drifting into Photorealism
    # It's explicitly designed to push towards a 2D graphic novel aesthetic.
    STYLE_ANCHOR = "2D vector art, flat coloring, clean lines, graphic novel style, cel shaded. (NEGATIVE PROMPT: 3d render, photorealistic, cinematic lighting, photography, bokeh, noise)"

    def run_task(self, user_id: str, trailhead_id: str):
        """
        Orchestration Method:
        1. Loads the Storybook Manifest.
        2. Iterates through every page.
        3. Generates a rigorous 'Directed Prompt'.
        4. Saves the manifest back to the DB, ready for the Illustrator.
        """
        logger.info(f"Starting Director Job for Trailhead {trailhead_id}")

        # 1. Fetch Trailhead
        try:
            # Using direct DB access for consistency with your codebase patterns
            response = self.db.table("Trailheads").select("*").eq("id", trailhead_id).eq("user_id", user_id).single().execute()
            trailhead = response.data
            if not trailhead:
                logger.error("Trailhead not found.")
                return
        except Exception as e:
            logger.error(f"Database error fetching trailhead: {e}")
            return

        manifest = trailhead.get('content', {})
        if not manifest or 'pages' not in manifest:
            logger.error("Invalid manifest format: No 'pages' found.")
            return

        pages = manifest.get('pages', [])
        updated_pages = []
        
        # 2. The Directing Loop
        for page in pages:
            page_num = page.get('page_number')
            narrative = page.get('narrative_text', '')
            visual_idea = page.get('visual_idea', '') # V2 Storybook output
            
            # Fallback if visual_idea is missing (V1 compatibility)
            if not visual_idea:
                visual_idea = page.get('visual_prompt', 'A scene matching the text.')

            logger.info(f"Directing Page {page_num}...")
            
            # Generate the Rigorous Spec
            final_prompt = self.construct_scene_prompt(narrative, visual_idea, trailhead_id) # Pass ID directly as per method sig
            
            # Save it as 'visual_prompt' so Illustrator knows what to use
            page['visual_prompt'] = final_prompt
            page['director_status'] = 'complete'
            updated_pages.append(page)

        # 3. Save Updates
        manifest['pages'] = updated_pages
        manifest['director_status'] = "completed"

        try:
            self.db.table("Trailheads").update({"content": manifest}).eq("id", trailhead_id).execute()
            logger.info("Successfully saved Directed Manifest to Database.")
        except Exception as e:
            logger.error(f"Error saving updates: {e}")

    def construct_scene_prompt(self, narrative_text: str, visual_idea: str, trailhead_id: str) -> str:
        """
        Main Pipeline for generating a detailed image prompt:
        1. Load Asset Bank (Immutable Character/Object descriptions) from the VOLUME (The Bible).
        2. Asset Locking: Identify active assets in the current scene and inject their descriptions.
        3. LLM Composition: Use the Director Prompt to decide camera angle, lighting, and environment.
        4. Final Assembly: Concatenate all elements with the STYLE_ANCHOR for a rigorous output.
        """
        logger.info(f"DirectorAgent: Constructing scene prompt for trailhead {trailhead_id}")
        
        # 1. Load the "Bible" (Volume Manifest for Asset Bank)
        project_content = {} # Initialize to avoid UnboundLocalError
        try:
            # First, get the volume_id from the trailhead
            th_res = self.db.table("Trailheads").select("volume_id, content").eq("id", trailhead_id).single().execute()
            trailhead = th_res.data
            volume_id = trailhead.get('volume_id')
            
            # Get local style preference or default
            visual_style = trailhead.get('content', {}).get('style', 'Graphic Novel')

            asset_bank = {}
            if volume_id:
                # Fetch the Volume to get the Master Asset Bank
                # Use 'graph_structure' as that's where we stored the master_asset_bank
                vol_res = self.db.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
                if vol_res.data:
                    vol_data = vol_res.data
                    # The master_asset_bank is inside graph_structure
                    graph = vol_data.get('graph_structure', {}) 
                    asset_bank = graph.get('master_asset_bank', {})
            
            # Fallback to Trailhead local assets if Volume empty (for V2 compatibility)
            if not asset_bank:
                asset_bank = trailhead.get('content', {}).get('asset_references', {})

        except Exception as e:
            logger.error(f"DirectorAgent: Failed to load project assets for {trailhead_id}: {e}")
            asset_bank = {}
            visual_style = 'Graphic Novel'

        # 2. Asset Locking: Identify Cast in Scene
        # We strictly check if the Asset Name appears in the narrative text or visual idea.
        # Collect both the full descriptions and just the names for tracking.
        active_assets_descriptions = []
        active_asset_names = []

        for name, description in asset_bank.items():
            # Case-insensitive check for robustness.
            if name.lower() in narrative_text.lower() or name.lower() in visual_idea.lower():
                active_assets_descriptions.append(f"({name}: {description})")
                active_asset_names.append(name)

        logger.debug(f"Identified active assets: {active_asset_names}")

        # 3. Run the Director Prompt (LLM Composition)
        context = {
            "narrative_text": narrative_text,
            "visual_idea": visual_idea,
            "visual_style": project_content.get('style', 'Graphic Novel'), # Default to Graphic Novel
            "asset_definitions": json.dumps(active_assets_descriptions) if active_assets_descriptions else "No specific cast members identified." # Pass as string
        }

        try:
            response_text = self.llm.chat_completion(SCENE_VISUALIZER_PROMPT.format(**context), json_schema=None)
            scene_data = self._clean_and_parse_json(response_text)
            
            # Robustness check: specific fix for "list has no attribute get"
            if isinstance(scene_data, list):
                if len(scene_data) > 0 and isinstance(scene_data[0], dict):
                    logger.warning("DirectorAgent: LLM returned a list instead of a dict. Using first element.")
                    scene_data = scene_data[0]
                else:
                    logger.warning("DirectorAgent: LLM returned an unexpected list format. Using fallback.")
                    scene_data = {} # Trigger fallback below
            elif not isinstance(scene_data, dict):
                logger.warning(f"DirectorAgent: LLM returned invalid type {type(scene_data)}. Using fallback.")
                scene_data = {}

        except Exception as e:
            logger.error(f"DirectorAgent: LLM failed to generate scene data for {trailhead_id}: {e}. Raw response: {response_text}. Falling back to basic prompt components.")
            scene_data = {}

        # Fallback defaults if keys are missing or parsing failed
        if not scene_data.get('composition_description'):
             scene_data['composition_description'] = "Wide shot, dynamic composition, character focused"
        if not scene_data.get('environment_description'):
             scene_data['environment_description'] = "The setting as described in the narrative text"
        if not scene_data.get('lighting_description'):
             scene_data['lighting_description'] = "Dramatic, atmospheric lighting"

        # 4. The "Secret Sauce": String Concatenation > LLM Generation
        # We trust the LLM for high-level composition, but we FORCE the style and asset descriptions
        # via explicit string injection. This is critical for visual consistency.
        
        # Assemble the subject block with forced descriptions
        subject_block = "SUBJECTS: " + (" ".join(active_assets_descriptions) if active_assets_descriptions else "A mysterious figure")

        # Final prompt assembly
        final_prompt = (
            f"{self.STYLE_ANCHOR} :: " # Global style enforcement
            f"{scene_data.get('composition_description', '')} :: "
            f"{subject_block} :: " # Forced asset consistency
            f"ENVIRONMENT: {scene_data.get('environment_description', '')} :: "
            f"LIGHTING: {scene_data.get('lighting_description', '')} "
            "--ar 2:3 --stylize 250 --no text speech bubbles logos watermarks signatures blur noise artifacts distortion, low quality, bad anatomy, ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad art, blurred, watermark, grainy, signature, cut off, draft"
        )

        logger.info(f"DirectorAgent: Final Directed Prompt (truncated for log): {final_prompt[:200]}...")
        return final_prompt

    def _clean_and_parse_json(self, text: str) -> Dict:
        """Helper to strip markdown code blocks if present and parse JSON safely."""
        cleaned_text = text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```", 1)[1].split("```", 1)[0]
        return json.loads(cleaned_text.strip())