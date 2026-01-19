import uuid
import logging
from services.audio.processor import AudioProcessor
from db.session import get_db

# Configuration
GROUPING_WINDOW_SECONDS = 30  # Group dialogue into 30s chunks for better retrieval

logger = logging.getLogger(__name__)

class AudioAtomizer:
    def __init__(self, user_id, project_id):
        self.user_id = user_id
        self.project_id = project_id
        self.processor = AudioProcessor()
        self.db = get_db() # Returns Supabase Client

    def ingest(self, file_path, source_id):
        """
        1. Process Audio (Diarization)
        2. Group segments into coherent Atoms
        3. Save to DB with Meta-Instructions
        """
        print(f"🎙️ Starting processing for: {file_path}")
        
        # 1. heavy lifting (GPU)
        try:
            raw_segments = self.processor.process_audio(file_path)
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise e
        
        # 2. Grouping Logic
        atom_payloads = self._group_segments(raw_segments)
        
        # 3. DB Insertion
        self._save_atoms(atom_payloads, source_id)
        
        print(f"✅ Created {len(atom_payloads)} atoms from audio.")

    def _group_segments(self, segments):
        """
        Merges rapid-fire dialogue into chunks of approx 30 seconds
        to ensure the AI has context when retrieving vectors.
        """
        if not segments:
            return []

        atoms = []
        current_chunk = []
        current_start = segments[0]['timestamp_start']
        
        for seg in segments:
            current_chunk.append(seg['formatted_string'])
            
            # If chunk is long enough, seal it
            if seg['timestamp_end'] - current_start >= GROUPING_WINDOW_SECONDS:
                atoms.append({
                    "content": "\n".join(current_chunk),
                    "start_time": current_start,
                    "end_time": seg['timestamp_end']
                })
                # Reset
                current_chunk = []
                current_start = seg['timestamp_end']
        
        # Catch any leftovers
        if current_chunk:
             atoms.append({
                "content": "\n".join(current_chunk),
                "start_time": current_start,
                "end_time": segments[-1]['timestamp_end']
            })
            
        return atoms

    def _save_atoms(self, payloads, source_id):
        atoms_to_insert = []
        for p in payloads:
            # The Magic Sauce: Meta Instructions
            # This tells the Agent HOW to interpret this text.
            instruction = (
                f"Transcript segment ({p['start_time']:.1f}s - {p['end_time']:.1f}s). "
                "Speakers are identified by tags [Speaker_XX]. "
                "Use this to track distinct viewpoints in a conversation."
            )

            # Construct dict for Supabase insert
            atom_data = {
                "user_id": self.user_id, 
                "name": f"Transcript Segment {p['start_time']:.0f}s-{p['end_time']:.0f}s", 
                "type": "concept", 
                "content": p['content'],
                "resolution_source_id": source_id,
                "meta_instruction": instruction,
                "metadata": {
                    "project_id": self.project_id,
                    "start_time": p['start_time'], 
                    "end_time": p['end_time'], 
                    "source_type": "audio_transcript"
                }
            }
            
            atoms_to_insert.append(atom_data)
        
        # Bulk insert
        if atoms_to_insert:
            try:
                # Using Supabase client to insert
                res = self.db.table("Atoms").insert(atoms_to_insert).execute()
                # Check for errors if needed, though supabase-py usually raises exception on error
            except Exception as e:
                logger.error(f"Error saving atoms to DB: {e}")
                raise e
