import logging
import json
import re
import os
import sys
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from db import crud, schemas
import numpy as np

# Add the project root to the path to import prompts correctly if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from prompts import SCRIPTING_PROMPT

logger = logging.getLogger(__name__)

class ScriptingAgent(BaseAgent):
    def run_task(self, trailhead_id: str, user_id: str, focus_area: Optional[str] = None, depth: str = "Broad"):
        logger.info(f"ScriptingAgent started for trailhead {trailhead_id} and user {user_id}. Focus: {focus_area}, Depth: {depth}")

        # 1. Fetch the Trailhead
        trailhead_response = self.db.table("Trailheads").select("*").eq("id", trailhead_id).eq("user_id", user_id).single().execute()
        if not trailhead_response.data:
            logger.error(f"Trailhead {trailhead_id} not found.")
            return
        trailhead = schemas.Trailhead(**trailhead_response.data)

        # 2. RAG / Context Retrieval
        # For now, since text_chunks might be empty, we use a fallback strategy.
        # Ideally, we would fetch embeddings, find chunks, etc.
        
        context_bundle = ""
        citation_map = {} # {source_id: title}

        # Fallback: If related_atom_ids exist, try to get context from them?
        # For the prototype test data, we have no related atoms.
        # So we will use the Trailhead's own insight as the "Seed Context" 
        # and potentially warn that no deep research was found.
        
        if trailhead.related_atom_ids:
            # Fetch atoms
            atoms = crud.get_atoms_for_user(self.db, user_id) # Optimisation needed later
            related_atoms = [a for a in atoms if a.id in trailhead.related_atom_ids]
            
            # For each atom, try to find source text (simplistic RAG)
            # This is expensive if we do it naively, so for now let's just list the atoms as context.
            context_bundle += "Related Concepts:\n"
            for atom in related_atoms:
                context_bundle += f"- {atom.name}\n"
                
            # Try to find source links
            links = crud.get_atom_source_links(self.db, trailhead.related_atom_ids)
            source_ids = list(set([l['source_id'] for l in links]))
            
            source_id_to_snippet = {} # New map for snippets

            if source_ids:
                sources = crud.get_sources_for_user(self.db, user_id)
                relevant_sources = [s for s in sources if s.id in source_ids]
                
                context_bundle += "\nSource Material Snippets (Simulated):\n"
                for s in relevant_sources:
                    citation_map[s.id] = s.title or "Untitled Source"
                    # If we had chunks, we'd use them. For now, take first 500 chars of raw_text if available
                    snippet = ""
                    if s.raw_text:
                        snippet = s.raw_text[:500].replace("\n", " ") + "..."
                        context_bundle += f"[cite: {s.id}] {snippet}\n\n"
                    
                    source_id_to_snippet[s.id] = snippet

        if not context_bundle:
            context_bundle = "No specific source text found in library. Proceed with a theoretical exploration based on the topic."

        # Construct steering instructions
        steering_instructions = f"Target Depth: {depth}."
        if focus_area:
            steering_instructions += f" Strict Focus Area: {focus_area}. Ensure the script connects the topic to this focus."

        # 3. Generate Script
        prompt = SCRIPTING_PROMPT.format(
            topic=trailhead.title,
            context=context_bundle,
            steering_instructions=steering_instructions
        )

        try:
            logger.info("Sending prompt to Gemini...")
            script_content = self.llm.generate_content(prompt)
            
            # 4. Post-process Citations (Trace Object Logic)
            citations_list = []
            citation_counter = 1
            citations_trace = {} # { "1": { ... } }
            
            def replace_citation(match):
                nonlocal citation_counter
                # match string is like "[cite: abc-123]"
                # extract ID
                c_id = match.group(0).replace("[cite: ", "").replace("]", "")
                
                if c_id in citation_map:
                    # Add to our list
                    citation_obj = {
                        "id": str(citation_counter),
                        "source_id": c_id,
                        "title": citation_map[c_id],
                        "snippet": source_id_to_snippet.get(c_id, "Snippet not available.")
                    }
                    citations_list.append(citation_obj)
                    citations_trace[str(citation_counter)] = citation_obj
                    
                    replacement = f"[{citation_counter}]"
                    citation_counter += 1
                    return replacement
                return match.group(0)

            # Use regex to replace all occurrences
            script_content = re.sub(r'\[cite: [a-zA-Z0-9-]+\]', replace_citation, script_content)
            
            # Convert to TipTap JSON format
            tiptap_content = self._text_to_tiptap_json(script_content)
            
            # Append References Section to TipTap content
            if citations_list:
                tiptap_content['content'].append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "References"}]
                })
                for cite in citations_list:
                     tiptap_content['content'].append({
                        "type": "paragraph",
                        "content": [{"type": "text", "text": f"[{cite['id']}] {cite['title']}"}]
                    })

            # 5. Update Trailhead with Wrapped Content
            # Wrapper Structure: { "doc": tiptap, "citations": trace }
            final_content_payload = {
                "doc": tiptap_content,
                "citations": citations_trace
            }

            self.db.table("Trailheads").update({
                "content": final_content_payload,
                # We don't have a status column in Trailhead schema yet, but maybe we should?
                # For now, just updating content is enough to show it in the editor.
            }).eq("id", trailhead_id).execute()

            logger.info(f"Script generated and saved for Trailhead {trailhead_id}.")

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            # Optionally save error state to DB

    def _text_to_tiptap_json(self, text: str) -> Dict[str, Any]:
        """
        Converts plain text (markdown-ish) to TipTap JSON structure.
        """
        lines = text.split('\n')
        content_nodes = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('## '):
                content_nodes.append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": line[3:]}]
                })
            elif line.startswith('# '):
                content_nodes.append({
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": line[2:]}]
                })
            else:
                content_nodes.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}]
                })
                
        return {
            "type": "doc",
            "content": content_nodes
        }
