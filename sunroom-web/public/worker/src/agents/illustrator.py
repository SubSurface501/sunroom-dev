import logging
import os
import time
from .base import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IllustratorAgent(BaseAgent):
    """
    The Visual Director.
    Responsible for turning text prompts into image assets using Google Imagen.
    """

    def run_task(self, user_id: str, trailhead_id: str, provider: str = "imagen"):
        logger.info(f"Starting Illustrator Job for Trailhead {trailhead_id}")

        # 1. Fetch the Storybook Manifest
        try:
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

        # Setup Output Directory
        # Saves to worker/output/images/{trailhead_id}/
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        output_dir = os.path.join(root_path, "worker", "output", "images", trailhead_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Saving images to: {output_dir}")

        output_dir = os.path.join(root_path, "worker", "output", "images", trailhead_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Saving images to: {output_dir}")

        # 2. Render Loop
        pages = manifest.get('pages', [])
        updated_pages = []

        for page in pages:
            page_num = page.get('page_number')
            # V2: Use the Director's output
            final_prompt = page.get('visual_prompt') 
            
            if not final_prompt:
                logger.warning(f"Skipping Page {page_num}: No prompt found.")
                updated_pages.append(page)
                continue
            
            file_name = f"page_{page_num:02d}.png"
            file_path = os.path.join(output_dir, file_name)
            
            # Skip if exists
            if os.path.exists(file_path) and page.get('image_url'):
                logger.info(f"Skipping Page {page_num} (already exists)")
                updated_pages.append(page)
                continue

            logger.info(f"Rendering Page {page_num}...")
            try:
                # Generate Image
                saved_path = self.llm.generate_image(final_prompt, file_path)
                
                if saved_path:
                    page['image_url'] = saved_path
                    time.sleep(4) # Rate limits
                else:
                    logger.error(f"Failed to generate image for page {page_num}")
            except Exception as e:
                logger.error(f"Error during generation: {e}")
            
            updated_pages.append(page)

        # 3. Save Updates
        manifest['pages'] = updated_pages
        manifest['illustration_status'] = "completed"

        try:
            self.db.table("Trailheads").update({"content": manifest}).eq("id", trailhead_id).execute()
            logger.info("Illustration job complete.")
        except Exception as e:
            logger.error(f"Error saving updates: {e}")
