import logging
import json
import re
from typing import Optional, Dict, List, Any
from .base import BaseAgent
from db import crud, schemas
import sys
import os

# Add the project root to the path to import prompts correctly if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from prompts import SEGMENTATION_PROMPT, INDEXING_PROMPT_SEGMENTED, FRONTIER_INDEXING_PROMPT

logger = logging.getLogger(__name__)

class IndexAtomAgent(BaseAgent):
    def run_task(self, source_id: str, user_id: str):
        logger.info(f"IndexAtomAgent started for source {source_id} and user {user_id}")

        # 1. Fetch the Source document
        source_response = self.db.table("Sources").select("*").eq("id", source_id).single().execute().data
        if not source_response:
            logger.error(f"Source {source_id} not found.")
            return
        source = schemas.Source(**source_response)

        if not source.raw_text:
            logger.warning(f"Source {source_id} has no raw_text. Skipping.")
            return

        previous_knowledge_state_summary = "No previous knowledge state available." # Default
        current_knowledge_state = {"evolutions": [], "frontier_nodes": [], "atoms": []} # Initialize for this source

        # If part of a series, fetch the previous knowledge state
        if source.series_id and source.series_index and source.series_index > 1:
            previous_sources_res = self.db.table("Sources").select("knowledge_state_snapshot") \
                                    .eq("series_id", source.series_id) \
                                    .lt("series_index", source.series_index) \
                                    .order("series_index", desc=True) \
                                    .limit(1).execute()
            if previous_sources_res.data and previous_sources_res.data[0]['knowledge_state_snapshot']:
                previous_knowledge_state_summary = json.dumps(previous_sources_res.data[0]['knowledge_state_snapshot'], indent=2)
                logger.info(f"Loaded previous knowledge state for series {source.series_id}, index {source.series_index-1}.")
        
        # 2. Segment the transcript
        logger.info(f"Segmenting transcript for source {source_id}...")
        segments = self._segment_transcript(source.raw_text)
        if not segments:
            logger.warning(f"Failed to segment transcript for source {source_id}. Fallback to full text indexing? No, skipping for now.")
            return
        
        logger.info(f"Identified {len(segments)} segments. Processing...")

        total_atoms_created = 0

        # 3. Process each segment
        for i, segment in enumerate(segments):
            segment_text = self._extract_segment_text(source.raw_text, segment.get('start_text'), segment.get('end_text'))
            
            # If extraction fails, or if it's the first/last segment and we missed the boundary, 
            # we might want to be more robust. For now, if empty, we skip.
            if not segment_text or len(segment_text) < 50:
                logger.warning(f"Could not locate text for segment {i+1}: '{segment.get('title')}'. Skipping.")
                continue

            logger.info(f"Indexing Segment {i+1}/{len(segments)}: {segment.get('title')}")
            
            # --- Use FRONTIER_INDEXING_PROMPT for series context, else fall back to basic indexing ---
            if source.series_id and source.series_index:
                frontier_analysis_data = self._analyze_frontier_for_segment(
                    segment_text=segment_text,
                    series_title=source.title or "Unknown Series Part",
                    series_index=source.series_index,
                    previous_knowledge_state_summary=previous_knowledge_state_summary
                )
                if frontier_analysis_data:
                    current_knowledge_state["evolutions"].extend(frontier_analysis_data.get("evolutions", []))
                    current_knowledge_state["frontier_nodes"].extend(frontier_analysis_data.get("frontier_nodes", []))
                    # For now, just store frontier nodes as atoms with a specific type
                    for node in frontier_analysis_data.get("frontier_nodes", []):
                        atom_name = node.get('concept')
                        if atom_name:
                             atom = schemas.Atom(
                                user_id=user_id,
                                name=atom_name,
                                type="frontier_node", # New atom type
                                metadata={"context": node.get("context"), "urgency": node.get("urgency")}
                            )
                             created_atom = crud.create_atom(self.db, atom=atom)
                             crud.link_atom_to_source(self.db, atom_id=created_atom.id, source_id=source_id)
                             total_atoms_created += 1


            # Original Atom extraction (can run alongside frontier analysis or conditionally)
            atoms_data = self._index_segment(
                segment_text=segment_text,
                video_title=source.title or "Unknown Video",
                segment_title=segment.get('title', f"Segment {i+1}"),
                segment_summary=segment.get('summary', "")
            )

            if atoms_data:
                for atom_obj in atoms_data:
                    atom_name = atom_obj.get('name')
                    atom_type = atom_obj.get('type')
                    
                    if not atom_name:
                        continue

                    db_type = "concept"
                    if atom_type == "Book Reference" or atom_type == "Book":
                        db_type = "book"
                    elif atom_type == "Entity":
                        db_type = "entity"
                    elif atom_type == "Person":
                        db_type = "person"
                    elif atom_type == "Claim":
                        db_type = "claim"
                    elif atom_type == "Question":
                        db_type = "question"

                    atom = schemas.Atom(
                        user_id=user_id,
                        name=atom_name,
                        type=db_type,
                        metadata={"description": atom_obj.get('description')}
                    )
                    
                    created_atom = crud.create_atom(self.db, atom=atom)
                    crud.link_atom_to_source(self.db, atom_id=created_atom.id, source_id=source_id)
                    total_atoms_created += 1
                    current_knowledge_state["atoms"].append(atom.dict())

        # 4. Update source with new knowledge state snapshot
        try:
            self.db.table("Sources").update({"knowledge_state_snapshot": current_knowledge_state}).eq("id", source_id).execute()
            logger.info(f"Updated knowledge_state_snapshot for source {source_id}.")
        except Exception as e:
            logger.error(f"Error updating knowledge_state_snapshot for source {source_id}: {e}")

        logger.info(f"Successfully created/linked {total_atoms_created} atoms for source {source_id}.")
        logger.info(f"IndexAtomAgent finished for source {source_id} and user {user_id}")

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
