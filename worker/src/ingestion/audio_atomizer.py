import uuid
import os
import logging

logger = logging.getLogger(__name__)

class AudioAtomizer:
    def __init__(self, db_client):
        self.db = db_client
        from worker.src.services.audio_processor import AudioProcessor
        self.processor = AudioProcessor()

    def process(self, file_path, source_id, project_id, user_id, hf_token, status_callback: callable = None):
        """
        Runs the full hearing pipeline and saves Atoms.
        """
        logger.info(f"Processing audio: {file_path}")
        
        def _callback(status):
            if status_callback:
                status_callback(status)

        # 1. Hear and Diarize
        try:
            raw_segments = self.processor.process_audio(file_path, hf_token, status_callback=status_callback)
            if not raw_segments:
                logger.warning("No segments found in audio.")
                _callback("failed")
                return 0
        except Exception as e:
            logger.error(f"Audio processing failed in processor: {e}")
            _callback("failed")
            raise

        # 2. Group into Memory Chunks
        _callback("indexing")
        chunks = self._group_segments(raw_segments)
        
        # 3. Save to Memory
        atoms_count = 0
        atoms_to_insert = []
        
        for chunk in chunks:
            instruction = (
                f"Transcript segment ({chunk['start']:.1f}s - {chunk['end']:.1f}s). "
                "Speakers are identified by tags [Speaker_XX]. "
                "Track distinct viewpoints."
            )
            
            atom_data = {
                "user_id": user_id,
                "resolution_source_id": source_id, # Linking to Source
                "content": chunk['content'],
                "meta_instruction": instruction,
                "type": "concept", # Default type
                "name": f"Transcript {source_id[:8]} {chunk['start']:.0f}s-{chunk['end']:.0f}s",
                "metadata": {
                    "type": "audio_transcript",
                    "start": chunk['start'],
                    "end": chunk['end'],
                    "project_id": project_id
                }
            }
            atoms_to_insert.append(atom_data)
            atoms_count += 1
            
        if atoms_to_insert:
            try:
                self.db.table("Atoms").insert(atoms_to_insert).execute()
                logger.info(f"Inserted {atoms_count} atoms for source {source_id}")
                _callback("completed") # Mark as completed after successful insertion
            except Exception as e:
                logger.error(f"Failed to insert atoms: {e}")
                _callback("failed")
                raise e
            
        return atoms_count

    def _group_segments(self, segments, window=30):
        """Merges dialogue into ~30s chunks"""
        if not segments:
            return []
            
        grouped = []
        current_text = []
        start_time = segments[0]['start']
        
        for seg in segments:
            current_text.append(seg['fmt_string'])
            if seg['end'] - start_time >= window:
                grouped.append({
                    "content": "\n".join(current_text),
                    "start": start_time,
                    "end": seg['end']
                })
                current_text = []
                start_time = seg['end']
        
        if current_text:
            # Handle case where segments might be empty or loop finishes
            end_time = segments[-1]['end'] if segments else start_time
            grouped.append({
                "content": "\n".join(current_text),
                "start": start_time,
                "end": end_time
            })
        return grouped
