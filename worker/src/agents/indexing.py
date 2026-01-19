import logging
import json
import re
from typing import Optional, Dict, List, Any
from .base import BaseAgent
from db import crud, schemas
import sys
import os
from datetime import datetime

# Add the project root to the path to import prompts correctly if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from prompts import SEGMENTATION_PROMPT, INDEXING_PROMPT_SEGMENTED, FRONTIER_INDEXING_PROMPT

logger = logging.getLogger(__name__)

class IndexAtomAgent(BaseAgent):
    def run_task(self, source_id: str, user_id: str):
        logger.info(f"Starting Indexing for Source {source_id} (vStatusFix)")
        
        # 1. Fetch Source Record
        source_record_res = self.db.table("Sources").select("raw_text, original_publication_date, date_confidence, metadata, author").eq("id", source_id).single().execute()

        if not source_record_res.data:
            logger.error(f"Source {source_id} not found for indexing.")
            return

        source_record = source_record_res.data
        source_text = source_record.get('raw_text')

        if not source_text:
                        return

        # 2. Chunking & Embedding Loop
        chunks = self._smart_chunk(source_text)
        logger.info(f"Source split into {len(chunks)} chunks.")
        
        # Fetch Source Global Date if available
        global_date = None
        global_confidence = 0.5
        d_str = source_record.get('original_publication_date')
        if d_str:
            try:
                global_date = datetime.fromisoformat(d_str.replace('Z', '+00:00'))
                global_confidence = source_record.get('date_confidence', 0.5)
            except: pass
        
        # Fetch Source Metadata & Author
        manual_lens_name = None
        source_author = None
        
        meta = source_record.get('metadata') or {}
        manual_lens_name = meta.get('manual_lens_name')
        source_author = source_record.get('author')
        universe_id_from_source = meta.get('universe_id') # New: Get universe_id from metadata
        discovery_epoch_id_from_source = meta.get('discovery_epoch_id') # New: Get discovery_epoch_id from metadata

        for i, chunk in enumerate(chunks):
            # 3. Atom Extraction (LLM)
            extraction_prompt = f"""
            Analyze the following text chunk. Extract the core independent concepts (Atoms).
            
            For each Atom, determine its Type:
            - "thought": A general concept, fact, or idea from the text.
            - "citation": A specific quote or idea attributed to someone ELSE within this text.
            - "entity", "person", "question": As standard.

            Metadata Rules:
            - If the text explicitly quotes or attributes an idea to a specific person (e.g. "Jung says..."), set 'original_author' to that person.
            - Otherwise, leave 'original_author' null.
            
            Text Chunk:
            {chunk[:2000]}
            
            Output JSON list: [{{ "name": "...", "type": "...", "definition": "...", "temporal_context": "...", "original_author": "..." }}]
            """
            
            try:
                response = self.llm.chat_completion(extraction_prompt)
                # Clean markdown
                if "```json" in response: response = response.split("```json")[1].split("```")[0]
                elif "```" in response: response = response.split("```")[1].split("```")[0]
                
                atoms_data = json.loads(response.strip())
                
                for atom_def in atoms_data:
                    # Determine Date
                    atom_date = global_date
                    atom_confidence = global_confidence
                    
                    local_time = atom_def.get('temporal_context')
                    if local_time:
                        try:
                            # Try parsing YYYY first
                            if len(str(local_time)) == 4:
                                atom_date = datetime(int(local_time), 1, 1)
                            else:
                                atom_date = datetime.fromisoformat(str(local_time))
                            atom_confidence = 0.9 # High confidence if explicit in text
                        except:
                            pass # Fallback to global

                    # Create Embedding
                    embedding = self.llm.get_embedding(f"{atom_def['name']}: {atom_def['definition']}")
                    
                    # Prepare Metadata
                    atom_metadata = {
                        "source_id": source_id,
                        "chunk_index": i,
                        "definition": atom_def['definition']
                    }
                    # Apply Manual Lens Tag if present
                    if manual_lens_name:
                        atom_metadata['cluster_name'] = manual_lens_name

                    # Determine Status
                    atom_status = "active"
                    if atom_def['type'] == 'question':
                        atom_status = 'open'
                        
                    # Determine Original Author
                    # Priority: 1. Citation Author, 2. Source Author
                    final_original_author = atom_def.get('original_author')
                    if not final_original_author and source_author:
                        final_original_author = source_author

                    # Create Atom Record
                    atom = schemas.Atom(
                        user_id=user_id,
                        name=atom_def['name'],
                        type=atom_def['type'],
                        content=atom_def['definition'],
                        embedding=embedding,
                        created_at_source=atom_date,
                        date_confidence=atom_confidence,
                        status=atom_status,
                        original_author=final_original_author,
                        universe_id=universe_id_from_source, # New: Pass universe_id
                        discovery_epoch_id=discovery_epoch_id_from_source, # New: Pass discovery_epoch_id
                        metadata=atom_metadata
                    )
                    
                    # Upsert Atom
                    created_atom = crud.create_atom(self.db, atom=atom)
                    
                    # Link Atom to Source
                    if created_atom and created_atom.id:
                        crud.link_atom_to_source(self.db, created_atom.id, source_id)

            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                continue
        
        # If Manual Lens, also create a "Seed Prose" atom to represent this lens in the UI (if not exists)
        if manual_lens_name:
            self._ensure_lens_atom(user_id, manual_lens_name, universe_id_from_source, discovery_epoch_id_from_source)

        logger.info(f"Indexing complete for Source {source_id}")
        # The categorization task will be triggered by the calling Celery task in tasks.py
        # to avoid a circular import.

    def _ensure_lens_atom(self, user_id: str, lens_name: str, universe_id: Optional[str] = None, discovery_epoch_id: Optional[int] = None):
        """
        Creates a placeholder Seed Prose atom so the lens appears in the UI.
        """
        # Check if exists
        # We query for type='seed_prose' and metadata->>'cluster_name' = lens_name
        # Or simpler: name = f"Lens: {lens_name}"? 
        # AutoGenesis uses type='seed_prose' and metadata={'cluster_name': ...}.
        # Let's match that pattern.
        
        # Note: We don't have a direct CRUD for this specific check easily without raw SQL or scanning.
        # But we can just upsert a specific named atom.
        atom_name = f"Lens: {lens_name}"
        
        # We need an embedding. We'll embed the name.
        embedding = self.llm.get_embedding(f"Lens context for {lens_name}")
        
        atom = schemas.Atom(
            user_id=user_id,
            name=atom_name,
            type="seed_prose",
            content=f"Manual lens for {lens_name}",
            embedding=embedding,
            metadata={"cluster_name": lens_name, "is_manual": True},
            universe_id=universe_id, # New: Pass universe_id
            discovery_epoch_id=discovery_epoch_id # New: Pass discovery_epoch_id
        )
        crud.create_atom(self.db, atom)
        logger.info(f"Ensured Lens Atom for {lens_name}")

    def _smart_chunk(self, text: str, max_chunk_size: int = 4000) -> List[str]:
        """
        Splits text into chunks that fit within the context window (roughly).
        Tries to split on newlines or periods.
        """
        chunks = []
        current_chunk = ""
        
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def _segment_transcript(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Uses the LLM to divide the transcript into logical segments.
        """
        truncated_transcript = transcript[:100000] 
        prompt = SEGMENTATION_PROMPT.format(transcript=truncated_transcript)
        
        try:
            response_text = self.llm.chat_completion(prompt, json_schema={"type": "object", "properties": {"segments": {"type": "array"}}, "required": ["segments"]})
            data = json.loads(response_text)
            return data.get("segments", [])
        except Exception as e:
            logger.error(f"Error during segmentation: {e}")
            return []

    def _index_segment(self, segment_text: str, video_title: str, segment_title: str, segment_summary: str) -> List[Dict[str, str]]:
        """
        Uses the LLM to extract atoms from a specific segment.
        """
        prompt = INDEXING_PROMPT_SEGMENTED.format(
            video_title=video_title,
            segment_title=segment_title,
            segment_summary=segment_summary,
            segment_text=segment_text
        )

        try:
            response_text = self.llm.chat_completion(prompt, json_schema={"type": "object", "properties": {"atoms": {"type": "array"}}, "required": ["atoms"]})
            data = json.loads(response_text)
            return data.get("atoms", [])
        except Exception as e:
            logger.error(f"Error indexing segment '{segment_title}': {e}")
            return []

    def _analyze_frontier_for_segment(self, segment_text: str, series_title: str, series_index: int, previous_knowledge_state_summary: str) -> Optional[Dict[str, Any]]:
        """
        Uses the LLM to identify knowledge evolution and frontier nodes within a segment.
        """
        prompt = FRONTIER_INDEXING_PROMPT.format(
            series_title=series_title,
            series_index=series_index,
            segment_text=segment_text,
            previous_knowledge_state_summary=previous_knowledge_state_summary
        )

        try:
            response_text = self.llm.chat_completion(prompt, json_schema={
                "type": "object",
                "properties": {
                    "evolutions": {"type": "array", "items": {"type": "object"}},
                    "frontier_nodes": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["evolutions", "frontier_nodes"]
            })
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Error during frontier analysis for series {series_title}, index {series_index}: {e}")
            return None

    def _extract_segment_text(self, full_text: str, start_text: Optional[str], end_text: Optional[str]) -> str:
        """
        Locates the substring in full_text bounded by start_text and end_text.
        Uses simple substring search.
        """
        if not start_text or not end_text:
            return ""
        
        # Clean up search terms (remove quotes, extra whitespace)
        start_text = start_text.strip().strip('"')
        end_text = end_text.strip().strip('"')

        # Find start index
        start_idx = full_text.find(start_text)
        if start_idx == -1:
             start_idx = full_text.find(start_text[:min(len(start_text), 20)]) # Try smaller chunk
        
        if start_idx == -1:
            return ""

        # Find end index (search AFTER start_idx)
        end_idx = full_text.find(end_text, start_idx)
        if end_idx == -1:
             end_idx = full_text.find(end_text[:min(len(end_text), 20)], start_idx)

        if end_idx == -1:
            return ""
        
        # Adjust end_idx to include the end_text length
        end_idx += len(end_text)

        return full_text[start_idx:end_idx]
