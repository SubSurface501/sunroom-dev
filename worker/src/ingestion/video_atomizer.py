import os
import logging
import asyncio
import shutil
from typing import List, Dict, Any
from worker.src.services.video_processor import VideoProcessor
from worker.src.services.vision import VisionService
from llm.client import get_llm_client

logger = logging.getLogger(__name__)

class VideoAtomizer:
    def __init__(self, db_client):
        self.db = db_client
        self.video_processor = VideoProcessor()
        # VisionService might need args, but init uses env vars
        self.vision_service = VisionService()
        self.llm_client = get_llm_client() # For embeddings

    def process(self, file_path: str, source_id: str, project_id: str, user_id: str) -> int:
        """
        Extracts frames, analyzes them, and stores Visual Atoms.
        Returns count of atoms created.
        """
        logger.info(f"Starting Video Atomization for {file_path}")
        
        # 1. Setup Temp Dir
        temp_dir = f"worker/output/frames_{source_id}"
        
        try:
            # 2. Extract Frames (Every 30s)
            frames = self.video_processor.extract_frames(file_path, temp_dir, interval=30)
            if not frames:
                logger.warning("No frames extracted.")
                return 0
            
            logger.info(f"Extracted {len(frames)} frames. Analyzing...")
            
            # 3. Analyze & Create Atoms
            atoms_to_insert = []
            
            # We run analysis sequentially to avoid rate limits on Vision API, 
            # though parallel with rate limiting would be faster.
            for timestamp, frame_path in frames:
                with open(frame_path, "rb") as f:
                    image_bytes = f.read()
                
                # Analyze (Async call needed)
                description = asyncio.run(self.vision_service.analyze_image(image_bytes))
                
                if not description or "Error" in description:
                    logger.warning(f"Failed to analyze frame at {timestamp}s")
                    continue
                
                # Embed description for semantic search
                embedding = self.llm_client.get_embedding(description)
                
                # Create Atom
                atom_data = {
                    "user_id": user_id,
                    "name": f"Visual Context @ {int(timestamp)}s",
                    "type": "visual_context",
                    "content": description,
                    "meta_instruction": f"Visual context at {int(timestamp)}s. Use this to ground the narrative.",
                    "resolution_source_id": source_id,
                    "embedding": embedding,
                    "metadata": {
                        "timestamp": timestamp,
                        "type": "frame",
                        "project_id": project_id,
                        # "media_url": ... we don't host frames permanently yet, maybe TODO
                    }
                }
                atoms_to_insert.append(atom_data)
            
            # 4. Insert Atoms
            if atoms_to_insert:
                logger.info(f"Inserting {len(atoms_to_insert)} visual atoms...")
                self.db.table("Atoms").insert(atoms_to_insert).execute()
                
                # Link to Source
                # We can do this in bulk if we get IDs back, or just rely on resolution_source_id query
                # Ideally, we create links in Atoms_to_Sources too.
                # Since insert might not return all IDs easily in all supabase clients without 'select',
                # and we rely heavily on 'resolution_source_id' for grouping, we might skip explicit link table for now
                # OR fetch the atoms back.
                # Let's rely on resolution_source_id which is the primary key for "Atoms belonging to Source".
                
            return len(atoms_to_insert)

        except Exception as e:
            logger.error(f"Video Atomization Failed: {e}", exc_info=True)
            return 0
        finally:
            # 5. Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp frames in {temp_dir}")
