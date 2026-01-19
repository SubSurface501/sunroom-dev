import logging
import time
import json
from .base import BaseAgent

logger = logging.getLogger(__name__)

class IllustratorAgent(BaseAgent):
    """
    The Visual Director.
    Responsible for turning text prompts into image assets using Google Imagen.
    """

    def run_task(self, user_id: str, node_id: str, provider: str = "imagen_4"):
        logger.info(f"Starting Illustrator Job for Node {node_id} (Provider: {provider})")

        # 1. Fetch the Storybook Manifest (from the Node's content)
        try:
            response = self.db.table("Nodes").select("*").eq("id", node_id).single().execute()
            node = response.data
            if not node:
                logger.error("Node not found.")
                return
        except Exception as e:
            logger.error(f"Database error fetching node: {e}")
            return

        manifest = node.get('content', {})
        if not manifest or 'pages' not in manifest:
            logger.error("Invalid manifest format: No 'pages' found in node content.")
            return

        # Setup Output Directory
        # Saves to worker/output/images/{node_id}/
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        output_dir = os.path.join(root_path, "worker", "output", "images", node_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Saving images to: {output_dir}")

        # 2. Render Loop
        pages = manifest.get('pages', [])
        updated_pages = []

        for page in pages:
            page_num = page.get('page_number')
            
            # Prioritize the Director's detailed prompt, with fallbacks
            final_prompt = page.get('final_visual_prompt') 
            if not final_prompt:
                final_prompt = page.get('visual_prompt')

            # --- SELF-HEALING: GENERATE PROMPT IF MISSING ---
            if not final_prompt:
                narrative_text = page.get('narrative_text')
                if not narrative_text:
                    logger.warning(f"Skipping Page {page_num}: No narrative text to generate a prompt from.")
                    updated_pages.append(page)
                    continue
                
                logger.info(f"Page {page_num} is missing a visual prompt. Generating one now...")
                try:
                    prompt_generation_prompt = f"""
                    Based on the following narrative text for a story page, create a concise, visually descriptive prompt for an AI image generator. 
                    Focus on characters, setting, mood, and key actions.
                    
                    NARRATIVE: "{narrative_text}"
                    
                    PROMPT:
                    """
                    final_prompt = self.llm.chat_completion(prompt_generation_prompt)
                    page['visual_prompt'] = final_prompt # Save the generated rough prompt
                    logger.info(f"Generated fallback prompt for Page {page_num}: {final_prompt[:100]}...")
                except Exception as e:
                    logger.error(f"Failed to generate prompt for Page {page_num}: {e}")
                    updated_pages.append(page)
                    continue
            # --- END SELF-HEALING ---

            if not final_prompt:
                logger.warning(f"Skipping Page {page_num}: No prompt found or could be generated.")
                updated_pages.append(page)
                continue
            
            file_name = f"page_{page_num:02d}.png"
            file_path = os.path.join(output_dir, file_name)
            
            if os.path.exists(file_path) and page.get('image_url'):
                logger.info(f"Skipping Page {page_num} (already exists and has a URL)")
                updated_pages.append(page)
                continue

            logger.info(f"Rendering Page {page_num}...")
            try:
                # Generate Image
                saved_path = None
                logger.info(f"Generating with {provider}: {final_prompt[:100]}...") # Log the prompt being used
                if provider == "vertex_sd":
                    saved_path = self.llm.generate_image_sd(final_prompt, file_path)
                elif provider == "imagen_4":
                    saved_path = self.llm.generate_image(final_prompt, file_path)
                else:
                    saved_path = self.llm.generate_image(final_prompt, file_path)
                
                if saved_path:
                    logger.info(f"Image saved to {saved_path}")
                    page['image_url'] = saved_path # Save local path for Publisher
                    if provider != "vertex_sd":
                         time.sleep(4)
                else:
                    logger.error(f"Failed to generate image for page {page_num}")
            except Exception as e:
                logger.error(f"Error during generation: {e}")
            
            updated_pages.append(page)

        # 3. Save Updates
        manifest['pages'] = updated_pages
        manifest['illustration_status'] = "completed"

        try:
            self.db.table("Nodes").update({"content": manifest}).eq("id", node_id).execute()
            logger.info("Illustration job complete.")
        except Exception as e:
            logger.error(f"Error saving updates: {e}")
