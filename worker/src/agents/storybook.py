import logging
import json
import os
import time
import sys
import math
import difflib
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from worker.src.agents.base import BaseAgent
from prompts import STORY_OUTLINER_PROMPT, STORY_PAGE_WRITER_PROMPT_V2, SCRIBE_RENDER_PROMPT
from db import crud, schemas
from worker.src.archetypes import ARCHETYPE_DEFINITIONS, DEFAULT_ARCHETYPE
from worker.src.context_frame import WorldBible, NarrativeLedger, ContextFrame, Entity, WorldLaw, EntityType, QuestState, Quest
from .energy_middleware import EnergyModelMiddleware
from .reviewer import ReviewAgent
from llm.client import LLMClient

logger = logging.getLogger(__name__)

class PageContentSchema(BaseModel):
    narrative_text: str = Field(..., description="The narrative prose for this page.")
    visual_idea: str = Field(..., description="A visual description for the illustrator.")

class StorybookAgent(BaseAgent):
    """
    The Writer V2.
    Fixes 'Caricature Loop' via Dynamic Ban Lists.
    Fixes 'Voice' via Style RAG (Retrieval-Augmented Generation).
    Implements Phase 2: Prose Tuning via Energy Models.
    """
    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        self.energy_middleware = EnergyModelMiddleware()
        
        # Model Tiering: Use a faster, more literal model for the Reviewer
        logger.info("Initializing 'Flash' client for Reviewer Agent...")
        # Pass the primary llm's debug mode to the new client
        reviewer_llm = LLMClient(debug_mode=llm.debug_mode) 
        # Manually override the model tier to use Flash for speed and literal-mindedness
        # V8.5 Fix: Use stable model IDs to prevent 404s
        reviewer_llm.model_tiers = ['models/gemini-2.0-flash-exp', 'models/gemini-1.5-flash']
        reviewer_llm.text_model_name = reviewer_llm.model_tiers[0]
        
        self.reviewer = ReviewAgent(db, worker, reviewer_llm)

    def run_task(self, user_id: str, node_id: str = None, volume_id: str = None, source_id: str = None, 
                 target_length: int = 12, visual_style: str = "Graphic Novel", assets: Dict = None,
                 transcript: str = None, dynamic_persona: Optional[Dict] = None, 
                 universe_ids: Optional[List[str]] = None, storyline_id: str = None,
                 character_stances: Optional[Dict] = None, seed_prose: Optional[str] = None,
                 prohibitions: Optional[List[str]] = None, archetype: Optional[str] = None,
                 start_state: Optional[Dict] = None,
                 world_bible: Dict[str, Any] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        logger.info(f"Starting Saga Generation V2 for user {user_id}. Volume: {volume_id}. Target Length Cap: {target_length} pages.")

        # 1. Load Context (The Brain) FIRST
        lesson_context, trailhead_title, node_constraints, simulation_trace = self._get_lesson_context(user_id, node_id, source_id)
        if not lesson_context:
            logger.error("Failed to retrieve lesson context.")
            return {}, {}

        # 2. NOW run the V14 "Dynamic Mirror" JIT Style RAG (The Soul)
        persona_name = "The Narrator"
        style_examples = "Neutral and objective narrative."

        try:
            logger.info("Performing JIT Style RAG for persona.")
            # Use the context we just loaded for the search
            query_embedding = self.llm.get_embedding(lesson_context)
            style_atoms = crud.match_atoms_by_embedding(
                self.db,
                query_embedding=query_embedding,
                match_threshold=0.7,
                match_count=3,
                query_user_id=user_id,
                filter_lenses=["seed_prose", "crystallized_thought"] # Broader style search
            )
            if style_atoms:
                style_examples = "**MIMIC THIS VOICE:**\n" + "\n".join([a['content'] for a in style_atoms])
                logger.info(f"JIT Style RAG: Found {len(style_atoms)} style samples.")
            else:
                 logger.warning("JIT Style RAG found no style samples for this user.")
        except Exception as e:
            logger.warning(f"JIT Style RAG failed: {e}")

        # NEW: Construct Truth Hierarchy Context and Prohibitions
        # V9 Change: World Bible is now passed in, not fetched.
        truth_hierarchy_context = "OMITTED FOR V9 DYNAMIC BIBLE"
        system_prompt_anchor = "OMITTED FOR V9 DYNAMIC BIBLE"
        
        # --- FETCH NARRATIVE LEDGER ---
        narrative_ledger = {}
        if universe_ids:
            try:
                # Use first universe as primary for state
                primary_uni_id = universe_ids[0]
                uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", primary_uni_id).single().execute()
                if uni_res.data and uni_res.data.get('active_epoch_id'):
                    epoch_id = uni_res.data['active_epoch_id']
                    ep_res = self.db.table("Epochs").select("narrative_ledger").eq("id", epoch_id).single().execute()
                    if ep_res.data:
                        narrative_ledger = ep_res.data.get('narrative_ledger') or {}
            except Exception as e:
                logger.warning(f"Failed to fetch narrative ledger: {e}")

        # --- NEW: FETCH STORY PATH CONTEXT (The "Anti-Loop" Shield) ---
        story_so_far_context = ""
        if volume_id and node_id:
            story_so_far_context = self._get_story_path_context(volume_id, node_id)
            if story_so_far_context:
                logger.info(f"Injecting Story Path Context ({len(story_so_far_context)} chars) to prevent loops.")

        # --- EPOCH STYLE RETRIEVAL ---
        epoch_style_desc = "Neutral narrative."
        try:
             # We can't access universe_id easily here if it's not passed, but we can try from volume
             uni_id_for_style = universe_ids[0] if universe_ids else None
             if not uni_id_for_style and volume_id:
                 vol_res = self.db.table("StoryVolumes").select("universe_id").eq("id", volume_id).single().execute()
                 if vol_res.data: uni_id_for_style = vol_res.data.get('universe_id')

             style_data = self.energy_middleware.retrieve_epoch_style(uni_id_for_style)
             if style_data:
                 epoch_style_desc, _ = style_data # Safe unpacking
                 logger.info(f"Epoch Style Injected: {epoch_style_desc[:50]}...")
             else:
                 epoch_style_desc = "Neutral and descriptive."
        except Exception as e:
            logger.warning(f"Failed to retrieve epoch style: {e}")
            epoch_style_desc = "Neutral and descriptive."


        # 3. Load Cast (The "Library")
        relevant_atoms = []
        if assets:
            characters_str = ", ".join([f"{k}: {v}" for k, v in assets.items()])
            artifacts_str = "Included in Character list" 
            logger.info("Using provided Master Asset Bank for cast.")
        else:
            person_atoms, book_atoms = self._get_cast_and_artifacts(
                user_id, 
                query_context=lesson_context, 
                universe_ids=universe_ids, 
                storyline_id=storyline_id # <--- ADD THIS PARAMETER
        )
            
            characters_str = ", ".join([f"{p['name']} ({p.get('metadata', {}).get('description', 'No description')})" for p in person_atoms]) if person_atoms else "A lone seeker"
            artifacts_str = ", ".join([f"{b['name']} ({b.get('metadata', {}).get('description', 'No description')})" for b in book_atoms]) if book_atoms else "Ancient texts"
            
            relevant_atoms.extend(person_atoms)
            relevant_atoms.extend(book_atoms)

        # --- 3.5 BUILD CONTEXT FRAME (THE SINGLE SOURCE OF TRUTH) ---
        context_frame, perception_manifest = self._build_context_frame(
            volume_id=volume_id, 
            node_id=node_id, 
            user_id=user_id, 
            universe_ids=universe_ids, 
            storyline_id=storyline_id, 
            seed_prose=seed_prose, 
            node_constraints=node_constraints, 
            previous_context=story_so_far_context, 
            relevant_atoms=relevant_atoms,
            simulation_trace=simulation_trace
        )
        logger.info("Context Frame & Perception Manifest Constructed.")

        # 4. PHASE 1: The Outline (The "Beat Sheet")
        logger.info("Phase 1: Drafting Dynamic Outline...")
        
        # --- DYNAMIC PACING LOGIC ---
        # Unpack constraints from node if available, otherwise fallback
        termination_condition = node_constraints.get("termination_condition")
        if not termination_condition:
            termination_condition = "The moment the specific objective described in the Lesson Context is achieved. DO NOT RESOLVE THE ENTIRE SAGA. End on a cliffhanger or transition."
            if seed_prose:
                 termination_condition = f"The moment this event concludes: '{seed_prose[:50]}...'. Do not go further."

        outline_prompt = STORY_OUTLINER_PROMPT.format(
            page_count=target_length, # Passed as a guide/cap
            lesson_context=seed_prose or f"The scene begins with the objective: {node_constraints.get('objective', 'Continue the story.')}",
            characters=characters_str,
            artifacts=artifacts_str,
            prohibitions_list_for_outline=system_prompt_anchor, 
            termination_condition=termination_condition
        )

        # Force Flash for Outline
        outline_response = self.llm.chat_completion(
            outline_prompt, 
            model="gemini-2.0-flash-exp", # Synchronized Model Name
            json_schema=None
        )
        try:
            beat_sheet = self._clean_and_parse_json(outline_response)[:target_length]
            if not isinstance(beat_sheet, list):
                raise ValueError("Outline is not a list")
            logger.info(f"Dynamic Outline generated with {len(beat_sheet)} beats (Cap was {target_length}).")
        except Exception as e:
            logger.error(f"Failed to generate or parse outline: {e}. Raw response: {outline_response}")
            return

        # 5. PHASE 2: The Writer (The "Page Loop")
        logger.info("Phase 2: Writing Pages...")
        pages = []
        previous_context_text = "The story begins."

        # V10: "Sovereign Hero" Type-Safe Protagonist Identification
        protagonist = next((e for e in world_bible.get('entities', {}).values() if (e.get('is_protagonist') if isinstance(e, dict) else getattr(e, 'is_protagonist', False))), None)

        if protagonist:
            protagonist_name = protagonist.get('name') if isinstance(protagonist, dict) else protagonist.name
        else:
            protagonist_name = "Anya" # Hard fallback to ensure the latch has a name to check
        
        identity_lock = f"**CRITICAL IDENTITY LOCK:** The protagonist's name is {protagonist_name}. You MUST use this name. Do not use any other name for the protagonist. Failure to do so will result in rejection of the text."


        # *** NEW: Build Character Anchor from World Bible ***
        character_anchor_text = ""
        if world_bible and "entities" in world_bible:
            anchors = []
            for key, entity in world_bible["entities"].items():
                # Correctly handle dictionary access
                entity_name = entity.get("name")
                entity_role = entity.get("role")
                if entity_name and entity_role:
                    e_pronouns = entity.get('pronouns', 'They/Them')
                    e_desc = entity.get('description', '')
                    
                    anchor_line = f"- {entity_name} ({e_pronouns}): {entity_role}. You must use these names. Their official name is '{entity_name}'."
                    forbidden = entity.get('forbidden_names')
                    if forbidden:
                        anchor_line += f" Do NOT use these names for them: {', '.join(forbidden)}."
                    if e_desc:
                        anchor_line += f" Traits: {e_desc}"
                    anchors.append(anchor_line)

            if anchors:
                character_anchor_text = (
                    "**[CHARACTER ANCHORS]**\n"
                    "CRITICAL: The following names and identities are LOCKED. You MUST use them. DO NOT CHANGE or DEVIATE from them.\n"
                    + "\n".join(anchors)
                    + "\n"
                )

        previous_location_name = None # V11.6
        all_bible_entities = world_bible.get('entities', {}).values() # V11.6 - Define once

        for i, beat in enumerate(beat_sheet):
            page_num = i + 1
            logger.info(f"Writing Page {page_num}/{len(beat_sheet)}...")

            # V11.6 - Get human-readable names for whitelisting
            current_loc_id = context_frame.ledger_snapshot.current_location if context_frame else "Unknown"
            current_loc_entity = world_bible.get('entities', {}).get(current_loc_id, {})
            current_loc_name = current_loc_entity.get("name", "an unknown location")

            current_inv = context_frame.ledger_snapshot.inventory if context_frame else []
            perceived_names = perception_manifest.get("visible_entities", []) if perception_manifest else []

            # V11.6 TONE SHIFT (Instructional Intent)
            absent_entities_desc = []
            
            protagonist_all_names_lower = set([protagonist_name.lower()])
            if protagonist and isinstance(protagonist, dict):
                if protagonist.get("pronouns"):
                    protagonist_all_names_lower.update([p.strip().lower() for p in protagonist.get("pronouns", "").split("/")])
                if protagonist.get("aliases"):
                    protagonist_all_names_lower.update([alias.lower() for alias in protagonist["aliases"]])

            for entity_data in all_bible_entities:
                entity_name_lower = entity_data.get('name', '').lower()
                if not entity_name_lower: continue
                if entity_name_lower in protagonist_all_names_lower: continue
                
                # An entity is absent if it's not the current location, not in inventory, and not perceived.
                # Also ensure it's not the previous location, which is allowed to be mentioned.
                if (entity_name_lower != current_loc_name.lower() and 
                    entity_name_lower not in [inv.lower() for inv in current_inv] and 
                    entity_data.get('name') not in perceived_names and
                    entity_name_lower != (previous_location_name.lower() if previous_location_name else '')):
                    absent_entities_desc.append(entity_data.get('name'))
            
            absent_block = ""
            if absent_entities_desc:
                # V11.6 - New Tone
                absent_block = (
                    f"**CANONICAL REALITY (DO NOT CONTRADICT):**\n"
                    f"- Anya is at {current_loc_name}.\n"
                )
                if previous_location_name:
                    absent_block += f"- Anya has recently left {previous_location_name}.\n"
                
                absent_block += f"- ABSENT: {', '.join(absent_entities_desc)}. You may MENTION these as memories or in dialogue, but Anya cannot physically INTERACT with them or enter them."


            # *** V9.5: Noun Cooldown (The "Flower Killer") ***
            style_constraint = ""
            if previous_context_text and len(pages) > 0: # Only apply after the first page
                stopwords = set(["the", "a", "an", "in", "is", "of", "and", "to", "was", "it", "her", "his", "she", "he", "with", "as", "at", "for", "from"])
                words = previous_context_text.lower().split()
                word_freq = {}
                for word in words:
                    cleaned_word = re.sub(r'[^\w\s]', '', word)
                    if cleaned_word and cleaned_word not in stopwords and len(cleaned_word) > 3:
                        word_freq[cleaned_word] = word_freq.get(cleaned_word, 0) + 1
                
                overused_nouns = [word for word, freq in word_freq.items() if freq > 3]
                if overused_nouns:
                    banned_list = ", ".join(overused_nouns)
                    style_constraint += f"\n**STYLE CONSTRAINT (NOUN COOLDOWN):** You have recently used the following terms: '{banned_list}'. Avoid these specific words."
            
            # --- V12: DYNAMIC CONTEXT PREPARATION ---
            # 1. Calculate the Acquisition Whitelist for this specific beat
            acquisition_whitelist = []
            if simulation_trace:
                for step in simulation_trace:
                    act = step.get('action', {})
                    if act.get('action_type', '').lower() in ['take', 'acquire', 'loot', 'grab']:
                        target = act.get('target_id')
                        if target: acquisition_whitelist.append(target)

            review_feedback = ""
            final_page_data = None
            
            for attempt in range(3):
                # 2. Format Physics Trace (The Ground Truth)
                trace_str = "No physical actions recorded."
                if simulation_trace:
                    steps = []
                    for s in simulation_trace:
                        act = s.get('action', {})
                        res = s.get('result', {})
                        steps.append(f"- ACTION: {act.get('action_type')} {act.get('target_id')} | RESULT: {res.get('message')}")
                    trace_str = "\n".join(steps)

                # 3. Information Quarantine (Blindfold the AI to the future)
                current_objective = beat.get('objective', beat) if isinstance(beat, dict) else beat
                page_prompt = f"""
**CURRENT SCENE OBJECTIVE:** {current_objective}

**PHYSICS TRACE (WHAT ALREADY HAPPENED):**
{trace_str}

**PROSE BRIDGE (CONTINUE FROM HERE):**
{previous_context_text}
"""

                # 4. Assemble Ground Truth (The Cage)
                system_instruction_for_llm = f"""You are {persona_name}, a master fiction writer.

**GROUND TRUTH (Follow these rules carefully):**
1.  **Protagonist:** You must introduce the protagonist, {protagonist_name}, by name in the first paragraph.
2.  **Identity:** {identity_lock}
3.  **Character Naming:** Use official names from anchors. Never use nicknames or forbidden aliases.
4.  **Physical Reality:** {absent_block}
5.  **Style:** {style_constraint}
6.  **Characters:** {character_anchor_text}

**INSTRUCTION:**
Dramatize the scene with sensory detail. Stay in the present moment. Do not skip ahead.

**REJECTION FEEDBACK FROM PREVIOUS ATTEMPT:** 
{review_feedback}
"""

                def generate_page_draft(temperature=0.7):
                    # Soften JSON requirement by moving it to the instruction text
                    instruction_with_format = system_instruction_for_llm + '\n\n**FORMAT:** Return ONLY a valid JSON object: {"narrative_text": "...", "visual_idea": "..."}'
                    
                    resp = self.llm.chat_completion(
                        page_prompt,
                        model="gemini-2.0-flash-exp",
                        system_instruction=instruction_with_format,
                        temperature=temperature
                    )
                    
                    # Parse and handle Gemini's list-wrap quirk
                    page_raw = self._clean_and_parse_json(resp)
                    page_data = page_raw[0] if isinstance(page_raw, list) else page_raw
                    
                    if not isinstance(page_data, dict):
                        raise TypeError(f"Invalid format returned from LLM: {page_data}")

                    draft_prose = page_data.get('narrative_text', '')

                    # Vitality Latch (Minimum length)
                    min_len = 100 if page_num == 1 else 200
                    if len(draft_prose) < min_len:
                        raise ValueError(f"Draft too short ({len(draft_prose)} chars). Be more descriptive.")

                    # THE DEADBOLT: Force physics compliance BEFORE returning to Tuner
                    self._check_compliance_hard(
                        draft_text=draft_prose,
                        world_bible=world_bible,
                        protagonist_name=protagonist_name,
                        current_location=current_loc_name,
                        inventory=current_inv,
                        acquisition_whitelist=acquisition_whitelist,
                        instructional_text=current_objective,
                        present_entity_names=perceived_names,
                        previous_location_name=previous_location_name
                    )
                    return page_data

                # 5. Execute Tuning Loop
                try:
                    final_page_data = self.energy_middleware.tune_thought(generate_page_draft, attempts=2) # V14 Correction
                    if final_page_data:
                        break
                except Exception as e:
                    logger.warning(f"Scene Generation Page {page_num} Attempt {attempt} failed: {e}")
                    # Feedback Accumulation (The Nervous System)
                    new_error = str(e)
                    if new_error not in review_feedback:
                        review_feedback += f"\n- {new_error}"
                    time.sleep(10)
            
            if not final_page_data:
                raise ValueError(f"CANON CRITICAL FAILURE: Could not generate page {page_num} without violating Universe Rules after {attempt + 1} attempts. Last feedback: {review_feedback}")

            current_ledger_dict = context_frame.ledger_snapshot.dict() if context_frame else {}
            final_patch = self._analyze_state_changes(final_page_data.get('narrative_text', ''), current_ledger_dict)
            self._commit_ledger_update(volume_id, final_patch)
            
            final_page_data['page_number'] = page_num
            final_page_data['beat_summary'] = beat
            pages.append(final_page_data)
            
            last_text_block = final_page_data.get('narrative_text', '')[-1500:] 
            previous_context_text = (
                "**PREVIOUS SCENE ENDING:**\n"
                f"\"...{last_text_block}\"\n"
                "**INSTRUCTION:** Continue the story immediately from this point. Match the tone, names, and immediate physical positions. Do not summarize what just happened; continue the action forward."
            )
            previous_location_name = current_loc_name # V11.6 - BATON PASS
            time.sleep(1)

        # 6. Save Output
        existing_content = {}
        if node_id:
            try:
                res = self.db.table("Nodes").select("content").eq("id", node_id).single().execute()
                if res.data:
                    existing_content = res.data.get('content') or {}
            except Exception as e:
                logger.warning(f"Could not fetch existing content for Node {node_id} to preserve: {e}")

        # 6. Final State Audit
        ending_state = {}
        if pages:
             full_node_text = "\n".join([p.get('narrative_text', '') for p in pages])
             ending_state = self._extract_ending_state(full_node_text)

        manifest = existing_content.copy()
        manifest.update({
            "project_title": f"Saga: {trailhead_title}",
            "theme": lesson_context[:100],
            "style": visual_style,
            "narrator_voice_check": f"Narrated by {persona_name}, with dynamic phrase modulation.",
            "pages": pages,
            "citations": [atom['id'] for atom in relevant_atoms],
            "ending_state": ending_state # <--- V4 MEMORY PASS
        })

        # --- V9.8: ENTITY DISCOVERY ---
        # After the node is fully written, scan it for new entities to add to the bible for the next node.
        full_text = " ".join([p.get('narrative_text', '') for p in pages])
        updated_bible = self._discover_entities(full_text, world_bible)

        return manifest, updated_bible

    def _discover_entities(self, text: str, current_bible: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scans text for new potential entities and adds them to the World Bible.
        """
        logger.info("🕵️‍♂️ Scanning for new entities...")
        if not text: return current_bible

        existing_entities = [e.lower() for e in current_bible.get("entities", {}).keys()]
        existing_aliases = []
        for entity in current_bible.get("entities", {}).values():
            existing_aliases.extend([a.lower() for a in entity.get("aliases", [])])
        
        known_names = set(existing_entities + existing_aliases)

        from prompts import ENTITY_DISCOVERY_PROMPT
        prompt = ENTITY_DISCOVERY_PROMPT.format(
            text_to_scan=text[:8000], # Limit context size
            known_names=", ".join(list(known_names))
        )

        try:
            schema = {
                "type": "object",
                "properties": {
                    "new_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                                "type": {"type": "string", "enum": ["character", "location", "object"]}
                            },
                            "required": ["name", "role", "type"]
                        }
                    }
                },
                "required": ["new_entities"]
            }
            response = self.llm.chat_completion(prompt, json_schema=schema)
            discovered_data = self._clean_and_parse_json(response)
            
            if discovered_data and discovered_data.get("new_entities"):
                updated_bible = current_bible.copy()
                if "entities" not in updated_bible: updated_bible["entities"] = {}
                
                for entity in discovered_data["new_entities"]:
                    name = entity["name"]
                    if name.lower() not in known_names:
                        logger.info(f"✨ Discovered new entity: {name} ({entity['type']})")
                        updated_bible["entities"][name] = {
                            "name": name,
                            "role": entity["role"],
                            "description": f"Discovered in scene. Role: {entity['role']}",
                            "pronouns": "They/Them", # Default
                            "aliases": [],
                            "traits": ["Dynamically Discovered"],
                            "type": entity["type"]
                        }
                        known_names.add(name.lower()) # Add to set to avoid re-adding in same run
                return updated_bible

        except Exception as e:
            logger.error(f"Entity Discovery failed: {e}")
        
        return current_bible

    def _build_context_frame(self, volume_id: str, node_id: str, user_id: str, universe_ids: List[str], 
                            storyline_id: str, seed_prose: str, node_constraints: Dict, 
                            previous_context: str, relevant_atoms: List[Dict], simulation_trace: List[Dict] = None) -> Tuple[ContextFrame, Dict]:
        """
        Constructs the ContextFrame: The Single Source of Truth for the generation.
        Returns ContextFrame AND PerceptionManifest (dict).
        """
        # 1. Load Bible & Ledger
        # Use first universe as primary for laws
        primary_uni = universe_ids[0] if universe_ids else None
        bible = self._load_world_bible(primary_uni)
        
        epoch_id = None
        if primary_uni:
             try:
                 uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", primary_uni).single().execute()
                 epoch_id = uni_res.data.get('active_epoch_id')
             except: pass
        ledger = self._load_narrative_ledger(epoch_id)

        # 2. Filter Entities (Who is here?)
        # We Map relevant_atoms (RAG results) to Bible Entities if possible
        present_entities = []
        present_entity_names = set()

        # V9.9.5 FIX: The protagonist is ALWAYS present.
        protagonist_entity_data = next((e for e in bible.entities.values() if e.is_protagonist), None)
        if protagonist_entity_data:
            # Ensure we're using the Pydantic model if it's just a dict
            if isinstance(protagonist_entity_data, dict):
                 protagonist_entity = Entity(**protagonist_entity_data)
            else:
                 protagonist_entity = protagonist_entity_data
            
            present_entities.append(protagonist_entity)
            present_entity_names.add(protagonist_entity.name.lower())


        for atom in relevant_atoms:
            # If atom matches a bible entity, use the bible definition (truer)
            if atom['name'].lower() not in present_entity_names:
                if atom['name'] in bible.entities:
                    entity_data = bible.entities[atom['name']]
                    if isinstance(entity_data, dict):
                        entity_model = Entity(**entity_data)
                    else:
                        entity_model = entity_data
                    present_entities.append(entity_model)
                else:
                    # Otherwise, create a temporary entity from the atom
                    present_entities.append(Entity(
                        name=atom['name'],
                        type=EntityType.OBJECT if atom.get('type') == 'concept' else EntityType.CHARACTER,
                        description=atom.get('content', 'No desc'),
                        immutable_traits=[]
                    ))
                present_entity_names.add(atom['name'].lower())

        # 3. Determine Constraints
        immediate_goal = node_constraints.get("objective", "Advance the plot.")
        termination_condition = node_constraints.get("termination_condition", "Scene completion.")
        
        # 4. Build Perception Manifest (V8)
        # Aggregate sensory data from the Simulation Trace
        location_visuals = {}
        sensory_details = {
            "visual": "Not specified.",
            "sound": "Not specified.",
            "detail": "Not specified."
        }
        
        if simulation_trace:
            for step in simulation_trace:
                result = step.get('result', {})
                if result.get('sensory_data'):
                    # Merge sensory data, overwriting with more recent info
                    for key in sensory_details.keys():
                        if key in result['sensory_data']:
                            sensory_details[key] = result['sensory_data'][key]
                    
                    # Check for location details (Atmosphere)
                    if 'visual' in result['sensory_data']:
                        location_visuals['atmosphere'] = result['sensory_data']['visual']

        # Use ProceduralGenerator for environment_feature if available and not set by trace
        environment_feature = "Nothing of note in the distance."
        if bible.world_seed and not location_visuals.get('feature'):
            from worker.src.simulation.procedural import ProceduralGenerator
            proc_gen = ProceduralGenerator(bible.world_seed)
            proc_details = proc_gen.generate_location_details(ledger.current_location)
            environment_feature = proc_details.get('feature', environment_feature)
            if not location_visuals.get('atmosphere'):
                 location_visuals['atmosphere'] = proc_details.get('atmosphere', "A standard atmosphere.")
        
        location_visuals['feature'] = environment_feature

        # For atmosphere, ensure a fallback if not from trace
        if not location_visuals.get('atmosphere'):
            location_visuals['atmosphere'] = f"The echoing dampness of {ledger.current_location}"

        # Get character traits from the ledger's hard_state
        character_traits = ", ".join(ledger.hard_state.traits) if ledger.hard_state.traits else "None specified."

        perception_manifest = {
            "location_visuals": location_visuals,
            "visible_entities": [e.name for e in present_entities],
            "sensory_details": sensory_details,
            "character_internal_state": ledger.soft_state.mood,
            "character_traits": character_traits,
            "hard_state_inventory": ledger.inventory
        }

        context_frame = ContextFrame(
            active_laws=bible.laws,
            local_geography=ledger.current_location, # or fetch from Node context
            present_entities=present_entities,
            ledger_snapshot=ledger,
            previous_context=previous_context,
            immediate_goal=immediate_goal,
            termination_condition=termination_condition,
            required_inclusions=[],
            forbidden_concepts=bible.prohibitions
        )
        
        return context_frame, perception_manifest

    def _load_world_bible(self, universe_id: str) -> WorldBible:
        """
        Loads the strict World Bible from the DB, coercing loose JSON if necessary.
        """
        if not universe_id: return WorldBible()
        
        try:
            res = self.db.table("Universes").select("world_bible").eq("id", universe_id).single().execute()
            raw_data = res.data.get('world_bible') or {}
            
            # Helper to safely parse strict models from potentially loose data
            # For now, we just return a default strict model if the data is totally off,
            # or try to map what we can.
            
            # If the DB has the exact schema, this works:
            # return WorldBible(**raw_data)
            
            # If (likely) it's loose, we construct a partial one:
            entities = {}
            if "entities" in raw_data and isinstance(raw_data["entities"], dict):
                for k, v in raw_data["entities"].items():
                    # Minimal conversion
                    entities[k] = Entity(
                        name=v.get("name", k),
                        type=v.get("type", EntityType.CHARACTER), # Default
                        description=v.get("description", "No description"),
                        immutable_traits=v.get("immutable_traits", [])
                    )

            laws = []
            # We might need to extract laws from text if not structured
            
            return WorldBible(entities=entities, laws=laws)
            
        except Exception as e:
            logger.warning(f"Failed to load strict World Bible: {e}. Returning empty.")
            return WorldBible()

    def _load_narrative_ledger(self, epoch_id: int) -> NarrativeLedger:
        """
        Loads the mutable Narrative Ledger from the Epoch.
        """
        if not epoch_id: 
            return NarrativeLedger(current_location="Unknown", current_time="Unknown")
        
        try:
            res = self.db.table("Epochs").select("narrative_ledger").eq("id", epoch_id).single().execute()
            raw_data = res.data.get('narrative_ledger') or {}
            
            # Map legacy list-based ledger to new object if needed
            if isinstance(raw_data, list):
                # Legacy format was just a list of strings
                return NarrativeLedger(
                    current_location="Unknown", 
                    current_time="Unknown",
                    inventory=[],
                    character_states={"History": str(raw_data)}
                )
            
            # Safe Pydantic load (filtering extras)
            return NarrativeLedger(
                current_location=raw_data.get('current_location', 'Unknown'),
                current_time=raw_data.get('current_time', 'Unknown'),
                inventory=raw_data.get('inventory', []),
                character_states=raw_data.get('character_states', {}),
                flags=raw_data.get('flags', {})
            )
        except Exception as e:
            logger.warning(f"Failed to load strict Narrative Ledger: {e}. Returning empty.")
            return NarrativeLedger(current_location="Unknown", current_time="Unknown")

    def _extract_ending_state(self, text: str) -> Dict:
        """Audits the generated prose to extract the final world state."""
        logger.info("Auditing Scene for State Snapshot...")
        from prompts import STATE_SNAPSHOT_PROMPT
        
        prompt = STATE_SNAPSHOT_PROMPT.format(text=text[:4000]) # Limit to 4k chars
        try:
            resp = self.llm.chat_completion(
                prompt, 
                model="models/gemini-2.5-flash",
                json_schema=None
            )
            return self._clean_and_parse_json(resp)
        except Exception as e:
            logger.error(f"State audit failed: {e}")
            return {}

    # --- Helpers ---

    def _get_lesson_context(self, user_id, node_id, source_id):
        lesson_context = ""
        title = "Untitled"
        constraints = {}
        simulation_trace = None

        if node_id:
            try:
                response = self.db.table("Nodes").select("*").eq("id", node_id).single().execute()
                node_data = response.data
                if node_data:
                    title = node_data.get('title', 'Untitled')
                    content = node_data.get('content') or {}
                    lesson_context = f"Title: {title}\nSummary: {content.get('summary', '')}"
                    constraints = content.get('constraints', {}) # Extract constraints from content JSONB
                    simulation_trace = content.get('simulation_trace') # V8 Logic
            except Exception as e:
                logger.error(f"Error fetching node: {e}")
                return None, None, {}, None
                
        elif source_id:
            logger.warning("Direct source processing for Saga not fully implemented.")
            return None, None, {}, None
        
        if not lesson_context:
            logger.error("No context found for lesson generation.")
            return None, None, {}, None
        return lesson_context, title, constraints, simulation_trace

    def _get_truth_hierarchy_context(self, user_id: str, universe_ids: Optional[List[str]], query_context: str, filter_storyline_id: Optional[str] = None) -> (str, List[str], str, Dict[str, Any]):
        """
        Constructs a truth hierarchy based on a Universe's 'Metaphysical Archetype'.
        This determines the fundamental physical laws and prohibitions for a story.
        Implements 'Conservative Inheritance': if any universe is MATERIALIST, it overrides all others.
        Returns the context string, a list of prohibitions, the system prompt anchor, and the World Bible.
        """
        hierarchy_context = ["--- METAPHYSICAL LAWS OF THIS UNIVERSE ---"]
        prohibitions = []
        system_prompt_anchor = "No specific archetype anchor found."
        active_archetype_name = DEFAULT_ARCHETYPE
        world_bible = {}

        try:
            # 1. Determine the governing Archetype (Conservative Inheritance)
            if universe_ids:
                res = self.db.table("Universes").select("archetype, world_bible").in_("id", universe_ids).execute()
                if res.data:
                    found_archetypes = [u['archetype'] for u in res.data if u.get('archetype')]
                    # Merge World Bibles (First one wins for now, or merge?)
                    # Simple strategy: Take the first non-empty world bible
                    for u in res.data:
                        if u.get('world_bible'):
                            world_bible = u['world_bible']
                            break
                            
                    if 'MATERIALIST' in found_archetypes:
                        active_archetype_name = 'MATERIALIST'
                    elif found_archetypes:
                        active_archetype_name = found_archetypes[0]
            
            logger.info(f"Governing Archetype for this session: {active_archetype_name}")

            # 2. Load prohibitions and anchor prompt from the Archetype definition
            archetype_def = ARCHETYPE_DEFINITIONS.get(active_archetype_name)
            if archetype_def:
                prohibitions = archetype_def.get("prohibited_concepts", [])
                system_prompt_anchor = archetype_def.get("system_prompt_anchor", "No anchor prompt defined.")
                hierarchy_context.append(system_prompt_anchor)
            else:
                logger.warning(f"Archetype '{active_archetype_name}' not found in definitions. No prohibitions will be applied.")

            # 3. Fetch Personal Knowledge + AMNESIA PROTOCOL
            query_embedding = self.llm.get_embedding(query_context)
            personal_knowledge_atoms = crud.match_atoms_by_embedding(
                self.db,
                query_embedding=query_embedding,
                match_threshold=0.7,
                match_count=5,
                query_user_id=user_id,
                filter_universe_ids=None,
                filter_permanence_types=[schemas.PermanenceType.STATIC.value, schemas.PermanenceType.ARCHETYPAL.value],
                filter_storyline_id=filter_storyline_id # CORRECTED
            )
            
            if personal_knowledge_atoms:
                hierarchy_context.append("\n--- PERSONAL KNOWLEDGE (SUBORDINATE TO UNIVERSE RULES) ---")
                for atom in personal_knowledge_atoms:
                    is_contaminated = any(prohibited_term.lower() in atom['content'].lower() for prohibited_term in prohibitions)
                    if is_contaminated:
                        logger.info(f"🚫 Amnesia Protocol: Purging contaminated atom '{atom['name']}' from context because it violates the '{active_archetype_name}' archetype.")
                    else:
                        hierarchy_context.append(f"- {atom['name']}: {atom['content']}")

        except Exception as e:
            logger.error(f"Error constructing truth hierarchy context: {e}")
            hierarchy_context = ["Error loading metaphysical context."]
            prohibitions = []
            system_prompt_anchor = "Error loading context."

        return "\n".join(hierarchy_context), prohibitions, system_prompt_anchor, world_bible

    def _get_cast_and_artifacts(self, user_id, query_context: str = "", universe_ids: Optional[List[str]] = None, storyline_id: Optional[str] = None):
        """
        Retrieves cast and artifacts using the match_atoms RPC function, filtered by universe and permanence.
        """
        if not query_context:
            logger.warning("No query context for cast/artifact search. This may lead to irrelevant results.")
            return [], []

        try:
            logger.info(f"Performing Semantic RAG for cast with query: {query_context[:50]}... | Universes: {universe_ids} | Storyline: {storyline_id}")
            query_embedding = self.llm.get_embedding(query_context)

            # For now, we always fetch the "World Bible" (static, archetypal)
            # In the future, we can add logic to include "dynamic" atoms if we are continuing a specific storyline.
            permanence_filter = [schemas.PermanenceType.STATIC.value, schemas.PermanenceType.ARCHETYPAL.value]

            # Fetch relevant people from the specified universe(s)
            person_atoms = crud.match_atoms_by_embedding(
                self.db,
                query_embedding=query_embedding,
                match_threshold=0.7,
                match_count=5,
                query_user_id=user_id,
                filter_lenses=["person"],
                filter_universe_ids=universe_ids,
                filter_permanence_types=permanence_filter,
                filter_storyline_id=storyline_id
            )
            
            # Fetch relevant artifacts/books from the specified universe(s)
            book_atoms = crud.match_atoms_by_embedding(
                self.db,
                query_embedding=query_embedding,
                match_threshold=0.7,
                match_count=5,
                query_user_id=user_id,
                filter_lenses=["book", "concept"],
                filter_universe_ids=universe_ids,
                filter_permanence_types=permanence_filter,
                filter_storyline_id=storyline_id
            )

            logger.info(f"RAG found {len(person_atoms)} people and {len(book_atoms)} artifacts.")
            return person_atoms, book_atoms

        except Exception as e:
            logger.error(f"Error in RAG cast retrieval: {e}")
            return [], []

    def _analyze_state_changes(self, new_content: str, current_ledger: Dict) -> Dict:
        """
        Analyzes new content and extracts a state patch (inventory adds, etc.).
        Returns the patch dict, does NOT write to DB.
        """
        try:
            # Use LLM to extract a "patch" of changes
            prompt = f"""
            You are a clinical State Analyst. Your sole purpose is to identify changes to a JSON state object based on a new piece of text.
            
            **Existing State JSON (for context):**
            {json.dumps(current_ledger, indent=2)}

            **Text to Analyze:**
            ---
            {new_content[:4000]} 
            ---
            
            **Instructions:**
            1.  Read the "Text to Analyze".
            2.  Identify any new events or state changes described in the text.
            3.  **QUEST TRACKING:** Look for 'active_quests' and 'current_goals'.
            4.  **INVENTORY (HARD LOGIC MODE):**
                Do not return the full inventory list. Instead, return two lists:
                "inventory_add": [items acquired in this text]
                "inventory_remove": [items lost, consumed, or given away]
            5.  Return a JSON object containing these keys or any other modified key-value pairs (like 'flags').
            6.  If no state changed, return an empty JSON object {{}}.

            **JSON Patch Output:**
            """
            
            llm_response = self.llm.chat_completion(
                prompt,
                model="models/gemini-2.5-flash"
            )
            
            try:
                cleaned_response = llm_response.strip().replace('`', '').replace('json', '')
                patch = json.loads(cleaned_response)
                return patch
            except json.JSONDecodeError:
                logger.error(f"State Analyst failed to decode LLM response into JSON patch: {llm_response}")
                return {}
        except Exception as e:
            logger.error(f"State analysis failed: {e}")
            return {}

    def _commit_ledger_update(self, volume_id: str, patch: Dict):
        """
        Applies a validated patch to the DB.
        """
        if not patch: return

        try:
            # 1. Get the active epoch
            vol_res = self.db.table("StoryVolumes").select("universe_id").eq("id", volume_id).single().execute()
            if not vol_res.data or not vol_res.data.get('universe_id'): return

            uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", vol_res.data['universe_id']).single().execute()
            if not uni_res.data or not uni_res.data.get('active_epoch_id'): return
            
            active_epoch_id = uni_res.data['active_epoch_id']
            
            # 2. Re-fetch current ledger to ensure atomic-ish update (though we are single threaded mostly)
            epoch_res = self.db.table("Epochs").select("narrative_ledger").eq("id", active_epoch_id).single().execute()
            if not epoch_res.data: return
            current_ledger = epoch_res.data.get('narrative_ledger', {})
            if isinstance(current_ledger, list): current_ledger = {}

            updated_ledger = current_ledger.copy()
            
            # --- HARD LOGIC 3: Python-Powered Inventory Enforcement ---
            if "inventory_add" in patch or "inventory_remove" in patch:
                current_inv = set(updated_ledger.get('inventory', []))
                
                # Add new items (Deduplicated by set)
                adds = patch.get('inventory_add', [])
                if isinstance(adds, list):
                    current_inv.update(adds)
                
                # Remove items
                removes = patch.get('inventory_remove', [])
                if isinstance(removes, list):
                    for item in removes:
                        if item in current_inv: 
                            current_inv.remove(item)
                
                updated_ledger['inventory'] = sorted(list(current_inv))
                # Clean up temporary keys
                patch.pop('inventory_add', None)
                patch.pop('inventory_remove', None)

            # Perform a deep-ish update for one level of nesting
            for key, value in patch.items():
                if isinstance(value, dict) and isinstance(updated_ledger.get(key), dict):
                    updated_ledger[key].update(value)
                else:
                    updated_ledger[key] = value

            # Write to DB
            if updated_ledger != current_ledger:
                self.db.table("Epochs").update({"narrative_ledger": updated_ledger}).eq("id", active_epoch_id).execute()
                logger.info(f"📚 Ledger Updated for Epoch {active_epoch_id}: {patch}")
            else:
                logger.info(f"📚 Ledger patch resulted in no net change.")

        except Exception as e:
            logger.error(f"Failed to commit ledger update: {e}")

    # Preserving legacy signature for compatibility if called elsewhere, but redirecting
    def _update_narrative_ledger(self, volume_id: str, new_content: str):
        # Fetch ledger first (inefficient but compatible)
        # This is a fallback if someone calls the old method
        # But we will replace usage in run_task
        pass # Deprecated in favor of the split flow

    # ... inside run_task loop ...
    # We need to find where _update_narrative_ledger was called and replace it with the new flow.


    def _check_compliance_hard(self, draft_text: str, world_bible: Dict[str, Any], protagonist_name: str, 
                               current_location: str = None, inventory: List[str] = None, 
                               acquisition_whitelist: Optional[List[str]] = None, 
                               instructional_text: Optional[str] = "",
                               present_entity_names: Optional[List[str]] = None,
                               previous_location_name: str = None):
        """
        V14.6: The Abstract Cage.
        Hard Python-based check against the World Bible's immutable facts.
        Now uses abstract, trait-based logic instead of hardcoded strings.
        """
        if not world_bible or not world_bible.get("entities"): return

        entities = world_bible["entities"]
        text_lower = draft_text.lower()
        
        # 1. Force everything to Dicts for consistent access
        normalized_entities = {}
        for k, v in entities.items():
            # Handle both Pydantic models and dictionaries
            if hasattr(v, 'dict'):
                normalized_entities[k] = v.dict()
            elif isinstance(v, dict):
                normalized_entities[k] = v
            else:
                logger.warning(f"Could not normalize entity: {k}")


        # 2. PROTAGONIST LATCH (Identity Deadbolt)
        protagonist_entity = next((e for e in normalized_entities.values() if e.get("is_protagonist")), None)
        protagonist_names = {protagonist_name.lower()} if protagonist_name else set()
        if protagonist_entity:
            protagonist_names.add(protagonist_entity.get("name", "").lower())
            if protagonist_entity.get("pronouns"):
                pronouns = [p.strip().lower() for p in protagonist_entity.get("pronouns", "").split("/")]
                protagonist_names.update(pronouns)
            if protagonist_entity.get("aliases"):
                protagonist_names.update([alias.lower() for alias in protagonist_entity["aliases"]])
        
        if not any(re.search(rf"\b{name}\b", text_lower, re.IGNORECASE) for name in protagonist_names if name):
            raise ValueError(f"Hard Compliance Fail: Protagonist '{protagonist_name}' or their alias is missing from the text.")

        # 3. NAME DISCIPLINE (Identity Dysmorphia Prevention)
        for entity_data in normalized_entities.values():
            forbidden_names = entity_data.get("forbidden_names", [])
            for forbidden_name in forbidden_names:
                if re.search(rf"\b{forbidden_name}\b", text_lower, re.IGNORECASE):
                    raise ValueError(f"Hard Compliance Fail: Forbidden name '{forbidden_name}' used. Use established names and aliases only.")

        # 4. ABSENT ENTITY LATCH (Trait-Based Physical Interaction)
        inv_lower = [i.lower() for i in inventory] if inventory else []
        present_entities_lower = [name.lower() for name in present_entity_names] if present_entity_names else []
        whitelist = [item.lower() for item in acquisition_whitelist] if acquisition_whitelist else []
        
        for entity_id, entity_data in normalized_entities.items():
            all_entity_names = {entity_data.get("name", "").lower()}
            all_entity_names.update([alias.lower() for alias in entity_data.get("aliases", [])])
            all_entity_names = {name for name in all_entity_names if name}

            # An entity is absent if NONE of its names are in inventory or present lists,
            # AND it's not the protagonist (who is always considered present implicitly).
            is_protagonist_name = any(name in protagonist_names for name in all_entity_names)
            is_present = is_protagonist_name or any(name in inv_lower or name in present_entities_lower for name in all_entity_names)
            
            if not is_present:
                for term in all_entity_names:
                    if term not in whitelist and re.search(rf"\b{term}\b", text_lower, re.IGNORECASE):
                        # This term for an absent entity was found. Now check for physical interaction.
                        INTERACTION_VERBS = ["entered", "inside", "at the", "within", "took", "grabbed", "using", "opened", "rode", "mounted", "approached", "walked to"]
                        MOUNT_VERBS = ["riding", "mounted"]
                        
                        verbs_to_check = INTERACTION_VERBS
                        entity_type = entity_data.get('type')
                        
                        # Use string comparison for robustness with different EntityType sources
                        if isinstance(entity_type, str) and entity_type.lower() == 'mount':
                             verbs_to_check = INTERACTION_VERBS + MOUNT_VERBS
                        elif isinstance(entity_type, EntityType) and entity_type == EntityType.MOUNT:
                             verbs_to_check = INTERACTION_VERBS + MOUNT_VERBS

                        context_match = re.search(rf"(.{{0,40}})\b{term}\b(.{{0,40}})", text_lower, re.IGNORECASE)
                        if context_match:
                            surrounding_text = context_match.group(0).lower()
                            if any(verb in surrounding_text for verb in verbs_to_check):
                                raise ValueError(f"Physical Violation: Character is interacting with absent '{term}' (Type: {entity_type}).")

        # 5. PERSPECTIVE LATCH (Anti-Report)
        report_markers = [
            "in this chapter", "the story continues", "the narrative follows",
            "it was observed that", "summary of events", "the author"
        ]
        for marker in report_markers:
            if re.search(rf"\b{marker}\b", text_lower, re.IGNORECASE):
                raise ValueError(f"Hard Compliance Fail: Perspective Shift. Found meta-commentary marker '{marker}'. Do not write a report or summary. Write the SCENE from inside the character's experience.")

        logger.info("Hard Compliance Check Passed.")

    def _clean_and_parse_json(self, text: str) -> Dict:
        """Helper to strip markdown code blocks if present and parse JSON safely."""
        cleaned_text = text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```", 1)[1].split("```", 1)[0]
        
        try:
            return json.loads(cleaned_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            logger.error(f"Raw Output causing failure: {text}")
            raise e



    def _get_story_path_context(self, volume_id: str, current_node_id: str) -> str:
        """
        Reconstructs the narrative arc leading up to the current node.
        Returns a string summarizing previous events to prevent looping.
        """
        try:
            # 1. Fetch Graph Structure
            vol_res = self.db.table("StoryVolumes").select("graph_structure").eq("id", volume_id).single().execute()
            if not vol_res.data or not vol_res.data.get('graph_structure'):
                return ""
            
            graph = vol_res.data['graph_structure']
            # nodes = {n['node_id']: n for n in graph.get('nodes', [])} # Unused
            edges = graph.get('connections', [])
            
            # 2. Build Parent Map (Child -> Parent) - Assuming Tree/DAG
            parent_map = {}
            for edge in edges:
                parent_map[edge['to']] = edge['from']
            
            # 3. Trace back from current_node to Root
            path = []
            pointer = current_node_id
            
            # Safety: Max depth 20 to prevent infinite loops
            for _ in range(20):
                parent_id = parent_map.get(pointer)
                if not parent_id:
                    break
                path.append(parent_id)
                pointer = parent_id
            
            # Reverse to get chronological order (Root -> Parent)
            path.reverse()
            
            if not path:
                return ""
                
            # 4. Fetch Content for Ancestors
            # We want the *generated prose* if it exists, otherwise the summary.
            nodes_res = self.db.table("Nodes").select("id, title, content").in_("id", path).execute()
            node_content_map = {n['id']: n for n in nodes_res.data}
            
            context_str = ""
            for i, node_id in enumerate(path):
                node_data = node_content_map.get(node_id)
                if not node_data:
                    continue
                
                title = node_data.get('title', 'Untitled')
                content = node_data.get('content') or {}
                
                # Try to get the *end* of the prose (Narrative State)
                pages = content.get('pages', [])
                if pages:
                    # If we have pages, the node is "Done". 
                    # Provide Architect's summary (Intent) + The Last Paragraph (Result).
                    arch_summary = content.get('summary', 'No summary.')
                    # Get last valid narrative text
                    last_page_text = "No text."
                    for p in reversed(pages):
                        if p.get('narrative_text'):
                            last_page_text = p.get('narrative_text')[-500:]
                            break
                            
                    node_summary = f"Summary: {arch_summary}\nEnding State: \"...{last_page_text}\""
                else:
                    # Fallback to Architect's summary
                    node_summary = content.get('summary', 'No summary available.')
                
                context_str += f"SEQUENCE {i+1}: [{title}]\n{node_summary}\n\n"
                
            return context_str

        except Exception as e:
            logger.error(f"Error building story path context: {e}")
            return ""