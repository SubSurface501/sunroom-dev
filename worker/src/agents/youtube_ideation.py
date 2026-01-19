import logging
import json
import os
import math
from typing import Dict, Any, List, Optional

from .base import BaseAgent
from db import crud, schemas

# Configure logging
logger = logging.getLogger(__name__)

# Define a schema for the LLM's expected JSON output
LLM_IDEA_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "cited_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The titles of the uploaded sources (videos/books) that inspired this specific idea. Choose from the provided list."
                    }
                },
                "required": ["title", "summary", "cited_sources"]
            }
        }
    },
    "required": ["ideas"]
}

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Compute the cosine similarity between two vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
        
    return dot_product / (norm_v1 * norm_v2)


class GeneratePerformanceDrivenIdeasAgent(BaseAgent):
    """
    An agent that generates new video ideas based on the knowledge frontier
    of a user's existing content, guided by their persona.
    """

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Simple text chunking function.
        """
        chunks = []
        if not text:
            return chunks
        
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end]
            chunks.append(chunk)
            if end == len(text):
                break
            start += chunk_size - overlap
        return chunks

    def _get_semantic_snippets(self, raw_text: str, atom_text: str, atom_vec: List[float], num_snippets: int = 3) -> List[str]:
        """
        Performs semantic search on raw text to find relevant snippets.
        """
        if not raw_text or not atom_text or not atom_vec:
            return []

        chunks = self._chunk_text(raw_text) # Call as a method
        if not chunks:
            return []

        # Cache for chunk embeddings to avoid re-computing if same chunk appears often (though less likely here)
        chunk_embedding_cache = {}
        scored_chunks = []

        for chunk in chunks:
            if chunk not in chunk_embedding_cache:
                chunk_embedding_cache[chunk] = self.llm.get_embedding(chunk)
            
            chunk_vec = chunk_embedding_cache[chunk]
            similarity = cosine_similarity(atom_vec, chunk_vec)
            scored_chunks.append({"chunk": chunk, "similarity": similarity})

        scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Format and limit snippets
        snippets = [f"...{sc['chunk']}..." for sc in scored_chunks if sc['similarity'] > 0.5][:num_snippets]
        logger.debug(f"Semantic snippets found: {len(snippets)}")
        return snippets

    def run_task(self, user_id: str, series_id: str = None, focus_area: str = None, depth: str = "Beginner"):
        """
        The main workflow for the agent. Generates new video ideas (Trailheads) based on
        the knowledge frontier and the user's defined persona.
        """
        logger.info(f"Starting performance-driven ideation for user_id: {user_id}, series_id: {series_id}, focus: {focus_area}, depth: {depth}")

        # 1. Load Persona
        persona_instruction = self._get_persona_instruction()
        if not persona_instruction:
            logger.error("Failed to load persona instruction. Aborting ideation.")
            return

        # 2. Find Next Logical Steps (Frontier Ideas)
        frontier_ideas = self._find_next_logical_steps(user_id, series_id) 
        if not frontier_ideas:
            logger.info("No new frontier ideas found to generate trailheads from.")
            return

        logger.info(f"Identified {len(frontier_ideas)} frontier ideas.")
        
        # 3. Generate New Ideas via LLM Prompt (using persona and frontier ideas)
        prompt = self._build_llm_prompt(frontier_ideas, persona_instruction, focus_area, depth)

        # Use JSON mode for reliable output
        response_text = self.llm.chat_completion(
            prompt,
            json_schema=LLM_IDEA_SCHEMA
        )
        ideas = self._parse_llm_response(response_text)

        # 4. Create Trailheads
        if not ideas:
            logger.warning("LLM failed to generate any new ideas from frontier analysis.")
            return

        trailhead_count = 0
        for idea in ideas:
            try:
                # For now, cite source titles from frontier_ideas for clarity
                cited_source_titles = []
                for f_idea in frontier_ideas:
                    # Basic heuristic: if the atom_name from frontier idea appears in the generated idea's summary, cite its source.
                    if f_idea.get('source_title') and f_idea.get('atom_name', '').lower() in idea['summary'].lower():
                        cited_source_titles.append(f_idea['source_title'])
                
                # Prepare content for JSONB column
                content_json = {
                    "summary": idea['summary'],
                    "cited_sources": cited_source_titles,
                    "focus_area": focus_area,
                    "depth": depth
                }
                
                full_insight = idea['summary']
                
                # Link related atom IDs from the frontier ideas that were used to generate this trailhead.
                related_atom_ids = [f_idea['atom_id'] for f_idea in frontier_ideas if 'atom_id' in f_idea] if frontier_ideas else []

                trailhead_create = schemas.TrailheadCreate(
                    user_id=user_id,
                    title=idea['title'],
                    insight=full_insight,
                    suggested_topic=idea['title'], # The idea itself is the suggested topic
                    type="frontier_idea", # New type for frontier-driven ideas
                    related_atom_ids=related_atom_ids,
                    content=content_json
                )
                crud.create_trailhead(self.db, trailhead=trailhead_create)
                trailhead_count += 1
            except Exception as e:
                logger.error(f"Failed to create trailhead for idea '{idea['title']}': {e}")

        logger.info(f"Successfully created {trailhead_count} new trailheads.")

    def _get_persona_instruction(self) -> Optional[str]:
        """
        Loads the system_prompt_instruction from the persona.json file.
        """
        # Adjust path to find persona.json in the project root
        persona_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'persona.json')
        try:
            with open(persona_file_path, 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
            return persona_data.get('system_prompt_instruction')
        except FileNotFoundError:
            logger.error(f"Persona file not found at {persona_file_path}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error decoding persona.json at {persona_file_path}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading persona: {e}")
            return None

    def _find_next_logical_steps(self, user_id: str, series_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Implements the 'High Gravity / Low Density' Frontier Scoring Algorithm.
        Now upgraded to use Semantic Saturation (Vector Similarity) instead of string matching.
        """
        logger.info(f"Finding next logical steps for user {user_id}, series {series_id}")
        
        # 1. Fetch Frontier Nodes
        query = self.db.table("Atoms").select("id, name, metadata").eq("user_id", user_id).eq("type", "frontier_node")
        
        res = query.execute()
        frontier_atoms = res.data if res.data else []
        
        if not frontier_atoms:
            logger.info("No frontier nodes found.")
            return []

        frontier_ids = [a['id'] for a in frontier_atoms]

        # 2. Fetch Links (Gravity Data)
        links_res = self.db.table("Atoms_to_Sources").select("atom_id, source_id").in_("atom_id", frontier_ids).execute()
        links = links_res.data if links_res.data else []
        
        # Map atom_id -> set of source_ids
        atom_sources_map = {}
        all_source_ids = set()
        for link in links:
            aid = link['atom_id']
            sid = link['source_id']
            if aid not in atom_sources_map:
                atom_sources_map[aid] = set()
            atom_sources_map[aid].add(sid)
            all_source_ids.add(sid)

        # 3. Fetch Source Details (Density Data)
        # Updated to fetch metadata for description embedding
        source_details = {}
        source_raw_text_cache = {}
        if all_source_ids:
             sources_res = self.db.table("Sources").select("id, title, metadata").in_("id", list(all_source_ids)).execute()
             if sources_res.data:
                 for s in sources_res.data:
                     # Store full object for access later
                     source_details[s['id']] = s
                     # Fetch and cache raw_text for contextual injection
                     raw_text = crud.get_source_raw_text(self.db, s['id'])
                     if raw_text:
                         source_raw_text_cache[s['id']] = raw_text

        # Cache for source embeddings to avoid re-calling API for same source across different atoms
        source_embedding_cache = {} 

        scored_ideas = []

        # 4. Calculate Scores & Build Atlas
        atlas_lines = ["\nFrontier Atlas (Top 10 Nodes):", "------------------------------"]

        for atom in frontier_atoms:
            aid = atom['id']
            name = atom['name']
            metadata = atom.get('metadata') or {}
            context = metadata.get('context', '')
            
            logger.debug(f"Processing atom: {name}, Context from metadata: {context}") # Debug log

            linked_source_ids = atom_sources_map.get(aid, set())
            gravity = len(linked_source_ids) # Count of unique sources mentioning this
            
            # --- Contextual Snippets for LLM Injection ---
            context_snippets = []
            for sid in linked_source_ids:
                if sid in source_raw_text_cache:
                    raw_text = source_raw_text_cache[sid]
                    keyword_lower = name.lower()
                    
                    # Robust keyword search using find() for all occurrences
                    start_search_idx = 0
                    while len(context_snippets) < 3:
                        match_idx = raw_text.lower().find(keyword_lower, start_search_idx)
                        if match_idx == -1:
                            break

                        # Extract a window of text around the keyword
                        start_idx = max(0, match_idx - 150) # 150 characters before
                        end_idx = min(len(raw_text), match_idx + len(name) + 150) # 150 characters after
                        snippet = raw_text[start_idx:end_idx].strip()
                        if snippet and f"...{snippet}..." not in context_snippets: # Avoid exact duplicates
                            context_snippets.append(f"...{snippet}...")
                        start_search_idx = match_idx + len(keyword_lower) # Continue search after this match
            
            # Fallback to semantic snippets if keyword search didn't yield enough
            if len(context_snippets) < 3:
                logger.debug(f"Keyword search insufficient for {name}, falling back to semantic search.")
                atom_text_for_semantic = f"{name}: {context}" # Re-use atom_text and atom_vec for semantic search
                atom_vec_for_semantic = self.llm.get_embedding(atom_text_for_semantic)
                
                for sid in linked_source_ids:
                    if sid in source_raw_text_cache:
                        raw_text = source_raw_text_cache[sid]
                        semantic_snips = self._get_semantic_snippets(
                            raw_text=raw_text,
                            atom_text=atom_text_for_semantic,
                            atom_vec=atom_vec_for_semantic,
                            num_snippets=3 - len(context_snippets) # Get remaining needed snippets
                        )
                        for snip in semantic_snips:
                            if snip not in context_snippets:
                                context_snippets.append(snip)
                            if len(context_snippets) >= 3:
                                break
                    if len(context_snippets) >= 3:
                        break

            logger.debug(f"Extracted snippets for {name}: {context_snippets}") # Debug log
            
            # --- Semantic Density Check ---
            # Create embedding for the Frontier Node (Name + Context)
            atom_text = f"{name}: {context}"
            atom_vec = self.llm.get_embedding(atom_text)
            
            max_similarity = 0.0
            primary_source_title = "Unknown Source"
            
            for sid in linked_source_ids:
                s_obj = source_details.get(sid)
                if not s_obj:
                    continue
                    
                stitle = s_obj.get('title', '')
                s_meta = s_obj.get('metadata') or {}
                s_desc = s_meta.get('description', '') or s_meta.get('summary', '')
                
                # Just-In-Time Embedding for Source (Title + Description)
                if sid not in source_embedding_cache:
                    source_text = f"{stitle}. {s_desc}"
                    # Limit text length to avoid token limits if descriptions are huge
                    source_embedding_cache[sid] = self.llm.get_embedding(source_text[:8000])
                
                source_vec = source_embedding_cache[sid]
                
                sim = cosine_similarity(atom_vec, source_vec)
                
                if sim > max_similarity:
                    max_similarity = sim
                    primary_source_title = stitle

            # Saturation Logic:
            # If similarity > 0.85, we consider this topic "Saturated" (already covered).
            is_saturated = max_similarity > 0.85
            
            # Penalty: Massive if saturated.
            density_penalty = 100.0 if is_saturated else 1.0
            
            # Add a small boost for "urgency" in metadata if present
            urgency_mult = 1.5 if metadata.get('urgency') == 'High' else 1.0
            
            score = ((gravity ** 2) * urgency_mult) / density_penalty
            
            if score > 0.1: # Filter noise
                scored_ideas.append({
                    "atom_id": aid,
                    "atom_name": name,
                    "source_title": primary_source_title, 
                    "insight": context,
                    "score": score,
                    "gravity": gravity,
                    "density": "High" if is_saturated else "Low",
                    "similarity_debug": f"{max_similarity:.2f}",
                    "context_snippets": context_snippets # Add snippets for LLM
                })

        # Sort by score
        scored_ideas.sort(key=lambda x: x['score'], reverse=True)
        
        # 5. Log the Atlas
        for idea in scored_ideas[:10]:
            atlas_lines.append(f"[+] \"{idea['atom_name']}\" (Score: {idea['score']:.2f} | G: {idea['gravity']} | D: {idea['density']} | Sim: {idea['similarity_debug']})")
            atlas_lines.append(f"     └─ Context: {idea['insight']}")
            if idea['context_snippets']:
                for snippet in idea['context_snippets']:
                    atlas_lines.append(f"       [Snippet]: {snippet}")
        
        logger.info("\n".join(atlas_lines))

        return scored_ideas[:5] # Return top 5 for LLM generation

    def _build_llm_prompt(self, frontier_ideas: List[Dict[str, Any]], persona_instruction: str, focus_area: str = None, depth: str = "Beginner") -> str:
        """
        Constructs the structured prompt for the LLM, incorporating persona and frontier insights.
        """
        
        # Format frontier ideas for context
        formatted_frontier_ideas = []
        for idea in frontier_ideas:
            previous_discussions_str = "None"
            if idea['context_snippets']:
                previous_discussions_str = "\n".join([f'    - "{s}"' for s in idea['context_snippets']])
            
            formatted_frontier_ideas.append(
                f"- Topic: {idea['atom_name']}\n  Insight: {idea['insight']}\n  Relevant Source: {idea['source_title']}\n  Previous Discussions: {previous_discussions_str}"
            )
        frontier_context_str = "\n".join(formatted_frontier_ideas)
        
        focus_instruction = ""
        if focus_area:
            focus_instruction = f"CRITICAL: All generated ideas MUST be strictly related to the focus area: \'{focus_area}\".\n"

        depth_instruction = f"The complexity level should be \'{depth}\'.\n"
        if depth == "Beginner":
            depth_instruction += " (Accessible, introductory, broad appeal).\n"
        elif depth == "Advanced":
            depth_instruction += " (Technical, esoteric, deep dive).\n"
        elif depth == "Pro":
            depth_instruction += " (Actionable, expert-level, cutting edge).\n"

        return f"""
{persona_instruction}

Your goal is to generate new, compelling video ideas based on the following unexplored 'Frontier Nodes' and 'Knowledge Evolutions' identified in the creator's content. Focus on creating *natural continuations* or *deeper dives* that build upon the existing narrative arc.

**FRONTIER INSIGHTS:**
{frontier_context_str}

**IMPORTANT: For "Previous Discussions", treat these as existing knowledge. Do NOT simply rephrase them. Instead, use them as a foundation to extend, contradict, or synthesize new ideas.**

Generate 5 new, compelling video ideas. Each idea should leverage one or more of the 'Frontier Insights' above, proposing a logical continuation or deeper exploration.
{focus_instruction}{depth_instruction}

For each idea:
1. Provide a title.
2. Provide a brief, insightful summary.
3. Identify 1-3 specific source titles from the 'Relevant Source' list above that inspired this idea (as 'cited_sources').

Respond with a JSON object matching this schema:
{json.dumps(LLM_IDEA_SCHEMA, indent=2)}
"""

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, str]]:
        """
        Parses the JSON response from the LLM.
        """
        try:
            data = json.loads(response_text)
            if "ideas" in data and isinstance(data["ideas"], list):
                # Ensure 'cited_sources' is a list of strings
                for idea in data["ideas"]:
                    if "cited_sources" in idea and not isinstance(idea["cited_sources"], list):
                        idea["cited_sources"] = [str(idea["cited_sources"])]
                    elif "cited_sources" not in idea:
                        idea["cited_sources"] = []
                return data["ideas"]
            else:
                logger.warning(f"LLM response was valid JSON but missed 'ideas' key: {response_text}")
                return []
        except json.JSONDecodeError:
            logger.error(f"Failed to decode LLM JSON response: {response_text}")
            return []
