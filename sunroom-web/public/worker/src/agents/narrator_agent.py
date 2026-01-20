import logging
import os
import time
from google.cloud import texttospeech
from .base import BaseAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarratorAgent(BaseAgent):
    """
    The Voice Actor.
    Responsible for turning text narratives into audio assets using Google Cloud Text-to-Speech.
    """

    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        self.tts_client = None

    def _get_tts_client(self):
        if not self.tts_client:
            try:
                self.tts_client = texttospeech.TextToSpeechClient()
            except Exception as e:
                logger.error(f"Failed to initialize TTS client: {e}")
                raise
        return self.tts_client

    def run_task(self, user_id: str, trailhead_id: str):
        logger.info(f"Starting Narrator Job for Trailhead {trailhead_id}")

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
        # Saves to worker/output/audio/{trailhead_id}/
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        output_dir = os.path.join(root_path, "worker", "output", "audio", trailhead_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Saving audio to: {output_dir}")

        # 2. Configure Voice
        # Using a deep, authoritative male voice to match the Persona (Dr. Sledge)
        # en-US-Journey-D is a good candidate for storytelling if available, otherwise Studio-M
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-D" # Journey voices are excellent for narration
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95, # Slightly slower for gravitas
            pitch=-1.0 # Slightly lower for authority
        )

        client = self._get_tts_client()
        pages = manifest.get('pages', [])
        updated_pages = []
        
        logger.info(f"Processing {len(pages)} pages for narration...")

        for page in pages:
            page_num = page.get('page_number')
            narrative_text = page.get('narrative_text')
            
            if not narrative_text:
                logger.warning(f"Page {page_num} has no text. Skipping.")
                updated_pages.append(page)
                continue

            # File Management
            file_name = f"narration_page_{page_num:02d}.mp3"
            file_path = os.path.join(output_dir, file_name)
            
            # Check if already exists
            if os.path.exists(file_path) and page.get('audio_url'):
                logger.info(f"Skipping Page {page_num} (already exists)")
                updated_pages.append(page)
                continue

            logger.info(f"Narrating Page {page_num}...")

            try:
                synthesis_input = texttospeech.SynthesisInput(text=narrative_text)

                response = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )

                with open(file_path, "wb") as out:
                    out.write(response.audio_content)
                
                page['audio_url'] = file_path
                # Sleep briefly to be a good API citizen
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to narrate page {page_num}: {e}")
                # Don't fail the whole job, just skip this page
            
            updated_pages.append(page)

        # 3. Save Updates
        manifest['pages'] = updated_pages
        manifest['narration_status'] = "completed"

        try:
            self.db.table("Trailheads").update({"content": manifest}).eq("id", trailhead_id).execute()
            logger.info("Successfully saved narrated manifest to Database.")
        except Exception as e:
            logger.error(f"Error saving updates: {e}")
