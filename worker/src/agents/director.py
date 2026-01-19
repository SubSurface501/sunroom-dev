import logging
import json
from .base import BaseAgent
from prompts import SCENE_VISUALIZER_PROMPT
from llm.client import LLMClient

logger = logging.getLogger(__name__)

class DirectorAgent(BaseAgent):
    """
    The Visual Director or Cinematographer.
    Translates a narrative page into a detailed, consistent visual prompt
    using a master asset bank to ensure congruency.
    """
    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        # Model Tiering: Use a faster, more literal model for the Director
        logger.info("Initializing 'Flash' client for Director Agent...")
        # Pass the primary llm's debug mode to the new client
        director_llm = LLMClient(debug_mode=llm.debug_mode) 
        # Manually override the model tier to use Flash for speed
        director_llm.model_tiers = ['models/gemini-1.5-flash-latest', 'models/gemini-2.5-flash']
        director_llm.text_model_name = director_llm.model_tiers[0]
        # Override the agent's LLM client with the new faster one
        self.llm = director_llm

    def run_task(self, node_id: str, assets: dict, visual_style: str):
        logger.info(f"Running Visual Director for Node {node_id}...")

        # 1. Fetch Node content
        try:
            node_res = self.db.table("Nodes").select("content").eq("id", node_id).single().execute()
            if not node_res.data or not node_res.data.get('content'):
                logger.error(f"DirectorAgent: Could not find content for node {node_id}.")
                return
            manifest = node_res.data['content']
        except Exception as e:
            logger.error(f"DirectorAgent: Error fetching node {node_id}: {e}")
            return

        pages = manifest.get('pages', [])
        if not pages:
            logger.warning(f"DirectorAgent: Node {node_id} has no pages to direct.")
            return
            
        # 2. Format Asset Bank for Prompt
        asset_definitions = "\n".join([f"- {name}: {desc}" for name, desc in assets.items()]) if assets else "No master assets provided."

        # 3. Iterate and Enrich Pages
        updated_pages = []
        for page in pages:
            page_num = page.get('page_number')
            narrative_text = page.get('narrative_text', '')
            visual_idea = page.get('visual_idea', '') # The rough idea from the writer

            if not narrative_text:
                updated_pages.append(page)
                continue

            logger.info(f"Directing scene for Page {page_num}...")
            
            # Construct the detailed prompt for the LLM
            director_prompt = SCENE_VISUALIZER_PROMPT.format(
                narrative_text=narrative_text,
                visual_idea=visual_idea,
                visual_style=visual_style,
                asset_definitions=asset_definitions
            )
            
            try:
                # Call LLM to get structured visual components
                response = self.llm.chat_completion(director_prompt, json_schema=None)
                if "```json" in response: response = response.split("```json")[1].split("```")[0]
                
                scene_data = json.loads(response.strip())

                # Assemble the final, detailed prompt
                final_prompt = f"{visual_style}. {scene_data.get('composition_description', '')}. {scene_data.get('environment_description', '')}. {scene_data.get('lighting_description', '')}. Featuring: {asset_definitions}"
                
                page['final_visual_prompt'] = final_prompt
                page['director_rationale'] = scene_data.get('rationale', '')
                
                logger.info(f"Page {page_num} directed successfully.")

            except Exception as e:
                logger.error(f"Director failed for Page {page_num}: {e}. Falling back to simple prompt.")
                # Fallback to the original idea if the director fails
                page['final_visual_prompt'] = f"{visual_style}. {visual_idea}. Featuring: {asset_definitions}"

            updated_pages.append(page)

        # 4. Save the updated manifest
        manifest['pages'] = updated_pages
        try:
            self.db.table("Nodes").update({"content": manifest}).eq("id", node_id).execute()
            logger.info(f"Successfully updated Node {node_id} with directed visual prompts.")
        except Exception as e:
            logger.error(f"DirectorAgent: Failed to save updated manifest for Node {node_id}: {e}")

class SimulationDirector:
    def __init__(self, db, worker, llm):
        self.db = db
        self.worker = worker
        self.llm = llm
        
    def run_task(self, *args, **kwargs):
        logger.warning("SimulationDirector is deprecated/stubbed in Phase 4.")
        return "Stubbed"
