import logging
import json
import os
import tempfile
from .base import BaseAgent
from db import crud, schemas
from pdfminer.high_level import extract_text
from worker.src.ingestion.audio_atomizer import AudioAtomizer # Import AudioAtomizer

logger = logging.getLogger(__name__)

class LibrarianAgent(BaseAgent):
    """
    The Archivist.
    Scans the header/beginning of a source to determine its Metadata (Author, Title).
    Also acts as the "Loader" for raw files (PDFs, Audio) if text is missing.
    """

    def _update_status(self, source_id: str, status: str):
        """Helper function to update the processing status of a source."""
        try:
            self.db.table("Sources").update({"processing_status": status}).eq("id", source_id).execute()
            logger.info(f"Source {source_id} status updated to: {status}")
        except Exception as e:
            logger.error(f"Failed to update status for source {source_id}: {e}")

    def run_task(self, source_id: str):
        logger.info(f"📚 Librarian scanning source {source_id}...")
        
        try:
            # 1. Fetch Source Data
            source_rec = self.db.table("Sources").select("*").eq("id", source_id).single().execute()
            if not source_rec.data:
                logger.error("Source record not found.")
                self._update_status(source_id, "failed")
                return
            
            source_data = source_rec.data
            source_text = source_data.get('raw_text') or ""
            storage_path = source_data.get('storage_path')
            
            # Use filename from storage_path for better consistency
            filename = storage_path.split('/')[-1] if storage_path else "Unknown"

            # 2. Text Extraction (If missing)
            if not source_text and storage_path:
                self._update_status(source_id, "downloading")
                logger.info(f"Downloading file from Supabase Storage: {storage_path}")
                try:
                    file_content_bytes = self.db.storage.from_("sources").download(storage_path)
                    logger.info(f"Successfully downloaded {len(file_content_bytes)} bytes.")

                    if file_content_bytes:
                        # Handle Audio Files
                        if filename.lower().endswith(('.mp3', '.mp4', '.m4a', '.wav')):
                            # The atomizer will handle its own status updates from here
                            logger.info("Audio file detected. Engaging AudioAtomizer...")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                                tmp.write(file_content_bytes)
                                tmp_path = tmp.name
                            
                            atomizer = AudioAtomizer(self.db)
                            hf_token = os.getenv("HF_TOKEN")
                            atomizer.process(
                                file_path=tmp_path, 
                                source_id=source_id,
                                project_id=None, # project_id is not available at this stage
                                user_id=source_data['user_id'],
                                hf_token=hf_token,
                                # Pass the status update callback
                                status_callback=lambda status: self._update_status(source_id, status)
                            )
                            os.remove(tmp_path)
                            logger.info("Audio processing handed off to AudioAtomizer.")
                            return "audio_processed" # Return status for audio

                        # Handle PDF
                        elif filename.lower().endswith('.pdf'):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(file_content_bytes)
                                tmp_path = tmp.name
                            
                            extracted_text = extract_text(tmp_path)
                            os.remove(tmp_path)
                        
                        # Handle Text
                        else:
                            extracted_text = file_content_bytes.decode('utf-8', errors='ignore')

                        if extracted_text:
                            source_text = extracted_text.replace('\x00', '')
                            self.db.table("Sources").update({"raw_text": source_text}).eq("id", source_id).execute()
                            logger.info(f"Successfully extracted {len(source_text)} chars from storage.")
                            # For text files, processing is now complete
                            self._update_status(source_id, "completed")
                        else:
                             logger.warning("Extraction yielded empty text.")
                
                except Exception as storage_err:
                    logger.error(f"Failed to download or process file from storage: {storage_err}", exc_info=True)
                    self._update_status(source_id, "failed")
                    return # Stop if we can't get the file

            if not source_text:
                logger.error("No text available for analysis.")
                return
            
            # We only need the first 5k chars to determine identity usually
            text_sample = source_text[:5000]
            
        except Exception as e:
            logger.error(f"Error fetching source: {e}")
            self._update_status(source_id, "failed")
            return

        # 3. LLM Analysis for Author/Title (for non-audio files)
        prompt = f"""
        You are an expert Archivist. Analyze the provided text fragment (the beginning of a document).
        Your goal is to extract the PRIMARY AUTHOR and TITLE.
        
        Rules:
        1. If it looks like a published book/paper, extract the real author/title.
        2. If it is a Transcript, identify the Speaker as Author.
        3. If it looks like a personal journal/note, set Author to "User" and Title to the filename or header.
        4. Be conservative. If unknown, return null.
        
        Filename: {filename}
        
        Text Sample:
        {text_sample}
        
        Return JSON: {{ "author": string | null, "title": string | null, "confidence": float }}
        """
        
        try:
            response = self.llm.chat_completion(prompt)
            if "```json" in response: response = response.split("```json")[1].split("```")[0]
            elif "```" in response: response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response.strip())
            
            author = data.get('author')
            title = data.get('title')
            
            if author or title:
                update_data = {}
                if author: update_data['author'] = author
                if title: update_data['title'] = title
                
                self.db.table("Sources").update(update_data).eq("id", source_id).execute()
                logger.info(f"Librarian tagged: {title} by {author}")
            else:
                logger.info("Librarian could not identify metadata.")

            return "text_extracted" # Return status for text
                
        except Exception as e:
            logger.error(f"Librarian scan failed: {e}")
            # Do not mark as failed if only metadata extraction fails
            pass
