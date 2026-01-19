import logging
import uuid
import json
from typing import Dict, List, Optional, Any
from db import crud, schemas
from llm.client import get_llm_client, LLMClient
from worker.src.agents.domain_expert import DomainExpertAgent
from worker.src.agents.reviewer import ReviewAgent, OntologicalCage, ReviewStatus
from worker.src.archetypes import ARCHETYPE_DEFINITIONS, DEFAULT_ARCHETYPE

logger = logging.getLogger(__name__)

class WritersRoomAgent:
    def __init__(self, db, worker):
        self.db = db
        self.llm = get_llm_client()
        # Worker is needed if DomainExpert uses sub-tasks, otherwise can be None
        self.domain_agent = DomainExpertAgent(db, worker, self.llm)
        
        # Initialize Reviewer with Flash Model for Speed & Strictness
        logger.info("Initializing 'Flash' client for Reviewer Agent in Writers Room...")
        reviewer_llm = LLMClient(debug_mode=self.llm.debug_mode) 
        # Manually override the model tier to use Flash
        reviewer_llm.model_tiers = ['models/gemini-2.0-flash-exp', 'models/gemini-1.5-flash']
        reviewer_llm.text_model_name = reviewer_llm.model_tiers[0]
        
        self.reviewer = ReviewAgent(db, worker, reviewer_llm)
        self.cage = OntologicalCage(self.reviewer)
        
        self.progress_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def _report(self, phase, percent, details):
        if self.progress_callback:
            self.progress_callback(phase, percent, details)
        logger.info(f"[{phase}] {details}")

    def execute_production_run(self, trailhead: Dict, volume_id: str, user_id: str):
        """
        Orchestrates the full lifecycle of a video essay production.
        """
        project_run_id = str(uuid.uuid4())
        logger.info(f"🎬 Opening Writers' Room: {project_run_id} for '{trailhead.get('title', 'Untitled')}'")
        
        # Phase 1: Subgraph Construction (The Research)
        self._report("Research", 10, "Initializing Subgraph Construction...")
        research_atoms = self._phase_research(trailhead, volume_id, user_id, project_run_id)
        
        # Phase 2: Structural Engineering (The Outline)
        self._report("Structure", 50, "Architecting Narrative Arc...")
        outline = self._phase_structure(trailhead, research_atoms, project_run_id)
        
        # Phase 3: The Draft (The Script)
        self._report("Drafting", 80, "Writing Final Script...")
        # Pass user_id to drafting phase for style injection
        # UPDATED: Pass volume_id for Ontology checks
        script, review_report = self._phase_drafting(trailhead, outline, research_atoms, user_id, volume_id)
        
        # Save Final Script Atom
        self._report("Complete", 95, "Finalizing...")
        try:
            script_atom = crud.create_atom(self.db, crud.schemas.Atom(
                content=script,
                type="video_script",
                name=f"Script: {trailhead.get('title', 'Untitled')}",
                user_id=user_id,
                embedding=self.llm.get_embedding(script),
                metadata={
                    "volume_id": volume_id, 
                    "run_id": project_run_id,
                    "subgraph_size": len(research_atoms),
                    "review": review_report # Store the audit in metadata
                }
            ))
            script_id = script_atom.id
        except Exception as e:
            logger.error(f"Failed to save script atom: {e}")
            script_id = "error_saving"
        
        self._report("Complete", 100, "Done.")
        return {
            "run_id": project_run_id,
            "script_id": script_id,
            "script": script,
            "review": review_report, # Return the audit to the frontend
            "subgraph_size": len(research_atoms)
        }

    def _phase_research(self, trailhead: Dict, volume_id: str, user_id: str, run_id: str) -> List[Dict]:
        logger.info("  🔬 Phase 1: Constructing Triangulated Subgraph...")
        
        # 1. Expand Questions
        expansion_prompt = f"""
        Project: {trailhead.get('title')}
        Premise: {trailhead.get('premise')}
        Lenses: {trailhead.get('agent_a', 'Analyst')} & {trailhead.get('agent_b', 'Creative')}
        
        Generate 5 specific research questions that bridge the Source Text and the User's Perspective.
        Return only the questions, one per line.
        """
        questions_text = self.llm.chat_completion(expansion_prompt)
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
        
        new_atoms = []
        total_q = min(len(questions), 5)
        
        for idx, q in enumerate(questions[:5]):
            if not q.strip(): continue
            self._report("Research", 10 + int((idx/total_q)*40), f"Triangulating Q{idx+1}: {q[:30]}...")
            
            # --- THE TRIAD SEARCH ---
            
            # A. The Self (User's Voice)
            embedding = self.llm.get_embedding(q)
            # Use query_user_id to search only user's thoughts
            user_atoms = crud.match_atoms_hybrid(self.db, q, embedding, 0.5, 3, query_user_id=user_id)
            user_context = "\n".join([f"[MY THOUGHT]: {a['content']}" for a in user_atoms])
            
            # B. The Source (The Library)
            # General search (broad context), filter out user's own thoughts to isolate "The Text" or "Other"
            # Note: match_atoms_hybrid by default searches everything if no filter. 
            # Ideally we filter by type='fact' or similar if we had strict types.
            # For now, we fetch generic and filter in python.
            source_candidates = crud.match_atoms_hybrid(self.db, q, embedding, 0.4, 10) 
            source_atoms = [a for a in source_candidates if a['user_id'] != user_id]
            source_context = "\n".join([f"[SOURCE TEXT]: {a['content']}" for a in source_atoms[:3]])
            
            # C. The World (External Validation)
            external_data = self.domain_agent.search_external_concepts(q[:100])
            external_context = "\n".join([f"[EXTERNAL CRITIC]: {r.get('title')} - {r.get('summary')}" for r in external_data])
            
            # --- SYNTHESIS ---
            synthesis_prompt = f"""
            Synthesize a core insight for the video essay '{trailhead.get('title')}'.
            Question: {q}
            
            Input A (My Mind): {user_context}
            Input B (The Text): {source_context}
            Input C (The World): {external_context}
            
            Task: Write a single, dense paragraph of insight that connects My Mind (A) to The Text (B), supported or challenged by The World (C).
            Perspective: Blend the analytical rigor of {trailhead.get('agent_a')} with the narrative flair of {trailhead.get('agent_b')}.
            """
            insight = self.llm.chat_completion(synthesis_prompt)
            
            # D. Save Project Node
            try:
                atom = crud.create_atom(self.db, crud.schemas.Atom(
                    content=insight,
                    type="project_node",
                    name=f"Insight: {q[:30]}...",
                    user_id=user_id,
                    embedding=self.llm.get_embedding(insight),
                    metadata={"volume_id": volume_id, "run_id": run_id, "is_subgraph": True}
                ))
                new_atoms.append({"id": atom.id, "content": insight})
            except Exception as e:
                logger.error(f"Failed to save project node: {e}")
            
        return new_atoms

    def _phase_structure(self, trailhead: Dict, research_atoms: List[Dict], run_id: str) -> str:
        logger.info("  📐 Phase 2: Architecting Narrative Structure...")
        
        # Feed the subgraph atoms into the Structuring Agent
        research_context = "\n".join([f"- {a['content']}" for a in research_atoms])
        
        prompt = f"""
        Create a Scene-by-Scene Outline for the video essay: '{trailhead.get('title')}'
        
        Available Research Subgraph (The Knowledge Base):
        {research_context}
        
        Requirements:
        1. Hook (The {trailhead.get('agent_a')} perspective)
        2. Development (The Conflict/Synthesis using the research)
        3. Conclusion (The {trailhead.get('agent_b')} perspective)
        
        Output purely the outline points.
        """
        return self.llm.chat_completion(prompt)

    def _get_universe_context(self, volume_id: str) -> (str, List[str], Dict[str, str], Dict[str, any], Dict[str, any]):
        """
        Fetches the Truth Hierarchy (Universe Laws) for the Volume.
        Epoch-Aware: Checks active_epoch_id first.
        Returns: (system_anchor, prohibitions, character_stances, narrative_ledger, world_bible)
        """
        try:
            # 1. Get Universe ID and Context from Volume
            vol = self.db.table("StoryVolumes").select("universe_id").eq("id", volume_id).single().execute()
            if not vol.data or not vol.data.get('universe_id'):
                return "Universe: Default Materialist Reality.", [], {}, {}, {}
                
            universe_id = vol.data['universe_id']
            
            # 2. Check for Active Epoch and World Bible
            uni_res = self.db.table("Universes").select("archetype, active_epoch_id, world_bible").eq("id", universe_id).single().execute()
            active_epoch_id = uni_res.data.get('active_epoch_id')
            world_bible = uni_res.data.get('world_bible', {})
            
            # 3. Epoch-Aware Fetch
            if active_epoch_id:
                epoch_res = self.db.table("Epochs").select("system_anchor, prohibitions, character_stances, narrative_ledger").eq("id", active_epoch_id).single().execute()
                if epoch_res.data:
                    logger.info(f"🔮 Loaded Active Epoch {active_epoch_id} Rules and Ledger.")
                    return (
                        epoch_res.data.get('system_anchor', ""), 
                        epoch_res.data.get('prohibitions', []),
                        epoch_res.data.get('character_stances', {}),
                        epoch_res.data.get('narrative_ledger', {}),
                        world_bible # Pass the world_bible through
                    )
            
            # 4. Fallback to Universe Archetype
            archetype_name = uni_res.data.get('archetype', DEFAULT_ARCHETYPE)
            logger.info(f"🔮 Using Fallback Archetype Rules: {archetype_name}")
            
            archetype_def = ARCHETYPE_DEFINITIONS.get(archetype_name)
            if not archetype_def:
                return f"Universe Archetype: {archetype_name}", [], {}, {}, world_bible
            
            anchor = archetype_def.get("system_prompt_anchor", "")
            prohibitions = archetype_def.get("prohibited_concepts", [])
            
            return anchor, prohibitions, {}, {}, world_bible
            
        except Exception as e:
            logger.error(f"Failed to fetch universe context: {e}")
            return "Universe Context Unavailable.", [], {}, {}, {}

    def _update_narrative_ledger(self, volume_id: str, new_content: str):
        """
        Analyzes new content, extracts a state patch, and safely merges it into the narrative ledger.
        """
        try:
            # 1. Get the active epoch for the volume's universe
            vol_res = self.db.table("StoryVolumes").select("universe_id").eq("id", volume_id).single().execute()
            if not vol_res.data or not vol_res.data.get('universe_id'): return

            uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", vol_res.data['universe_id']).single().execute()
            if not uni_res.data or not uni_res.data.get('active_epoch_id'): return
            
            active_epoch_id = uni_res.data['active_epoch_id']
            
            # 2. Get the current ledger (The Source of Truth)
            epoch_res = self.db.table("Epochs").select("narrative_ledger").eq("id", active_epoch_id).single().execute()
            if not epoch_res.data: return

            current_ledger = epoch_res.data.get('narrative_ledger', {})

            # 3. Use LLM to extract a "patch" of changes
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
            3.  **QUEST TRACKING:** Explicitly look for 'active_quests' and 'current_goals'. 
                - If a quest is accepted, add it to 'active_quests'.
                - If a quest is completed, move it to 'completed_quests'.
                - Update 'inventory' with any items acquired or lost.
            4.  Return a JSON object containing ONLY THE NEW OR MODIFIED key-value pairs.
            5.  If a nested object changes (like 'flags' or 'active_quests'), include the whole nested object.
            6.  If no state changed, return an empty JSON object {{}}.

            **JSON Patch Output:**
            """
            
            llm_response = self.llm.chat_completion(prompt)
            
            try:
                cleaned_response = llm_response.strip().replace('`', '').replace('json', '')
                patch = json.loads(cleaned_response)
            except json.JSONDecodeError:
                logger.error(f"State Analyst failed to decode LLM response into JSON patch: {llm_response}")
                return

            # 4. Safely merge the patch into the current ledger
            if patch:
                updated_ledger = current_ledger.copy()
                
                # Perform a deep-ish update for one level of nesting (e.g., for 'flags')
                for key, value in patch.items():
                    if isinstance(value, dict) and isinstance(updated_ledger.get(key), dict):
                        updated_ledger[key].update(value)
                    else:
                        updated_ledger[key] = value

                # Only write to DB if there's an actual change
                if updated_ledger != current_ledger:
                    self.db.table("Epochs").update({"narrative_ledger": updated_ledger}).eq("id", active_epoch_id).execute()
                    logger.info(f"📚 State Analyst Updated Ledger for Epoch {active_epoch_id}: {patch}")
                else:
                    logger.info(f"📚 State Analyst patch resulted in no net change for Epoch {active_epoch_id}.")
            else:
                logger.info(f"📚 State Analyst found no state changes for Epoch {active_epoch_id}.")

        except Exception as e:
            logger.error(f"Failed to update narrative ledger: {e}")

    def _check_compliance_hard(self, draft_text: str, world_bible: Dict[str, Any]):
        """
        Hard Python-based check against the World Bible's immutable facts.
        Raises ValueError on critical violation (e.g., forbidden names, missing protagonist).
        """
        if not world_bible or not world_bible.get("entities"): return

        entities = world_bible["entities"]
        
        # *** MODIFIED: Stricter Name Checking ***
        # Check for protagonist name AND forbidden names for all entities
        for entity_key, entity_data in entities.items():
            correct_name = entity_data.get("name")
            if not correct_name:
                continue # Skip if no official name is defined

            # Ensure the correct name appears
            if correct_name.lower() not in draft_text.lower():
                 # Allow for some flexibility, maybe the character is not in this scene
                logger.warning(f"Potential Compliance Issue: Entity '{correct_name}' not mentioned in draft.")

            # Check for forbidden names (aliases that cause identity drift)
            forbidden_names = entity_data.get("forbidden_names", [])
            for forbidden_name in forbidden_names:
                if forbidden_name.lower() in draft_text.lower():
                    raise ValueError(f"Hard Compliance Fail: Forbidden name '{forbidden_name}' detected for entity '{entity_key}'. The correct name is '{correct_name}'.")

        logger.info("Hard Compliance Check Passed.")


    def _summarize_beat_for_baton(self, beat_text: str) -> Dict[str, str]:
        """
        Analyzes a beat's text to create a structured "Narrative Baton" for the next beat.
        """
        prompt = f"""
        Analyze the following narrative beat. Your task is to extract key transitional details for the next writer.
        
        Text to Analyze:
        ---
        {beat_text}
        ---

        Instructions:
        1. Identify the character who spoke last. If no one spoke, say "Narrator".
        2. Describe the prevailing emotional tone at the END of the beat (e.g., "tense", "somber", "hopeful").
        3. Identify the most immediate open loop or unresolved action at the end of the beat. What is the very next thing that needs to happen or be addressed?

        Return a single JSON object with the keys "last_speaker", "emotional_tone", and "open_loop".
        
        JSON Output:
        """
        try:
            response = self.llm.chat_completion(prompt)
            cleaned_response = response.strip().replace('`', '').replace('json', '')
            baton = json.loads(cleaned_response)
            return baton
        except Exception as e:
            logger.error(f"Failed to create Narrative Baton: {e}")
            # Return a neutral baton on failure
            return {
                "last_speaker": "Unknown",
                "emotional_tone": "neutral",
                "open_loop": "The previous scene concluded."
            }

    # *** MODIFIED: ADDED previous_beat_prose parameter ***
    def _generate_atomic_beat(self, volume_id: str, user_id: str, beat_instruction: str, narrative_baton: Dict[str, str], previous_beat_prose: str = ""):
        """
        Generates a single, state-aware narrative beat using a structured Narrative Baton and Epoch Style.
        """
        # 1. READ: Fetch the LATEST state from the database
        style_samples = crud.get_style_samples(self.db, user_id, limit=1)
        user_style_context = "\n---\n".join(style_samples) if style_samples else "Use a smart, analytical voice."
        
        # --- EPOCH STYLE RETRIEVAL ---
        from .energy_middleware import EnergyModelMiddleware
        middleware = EnergyModelMiddleware()
        
        # Get Universe ID for the volume
        vol_res = self.db.table("StoryVolumes").select("universe_id").eq("id", volume_id).single().execute()
        uni_id = vol_res.data.get('universe_id') if vol_res.data else None
        
        epoch_style_desc, _ = middleware.retrieve_epoch_style(uni_id) if uni_id else ("Neutral narrative.", None)
        
        universe_anchor, prohibitions, char_stances, narrative_ledger, world_bible = self._get_universe_context(volume_id)

        # *** NEW: Build Character Anchor from World Bible ***
        character_anchor_text = ""
        if world_bible and "entities" in world_bible:
            anchors = []
            for key, entity in world_bible["entities"].items():
                if "name" in entity and "role" in entity:
                    anchors.append(f"- {key}: Name is '{entity['name']}', Role is '{entity['role']}'.")
            if anchors:
                character_anchor_text = (
                    "**[CHARACTER ANCHORS]**\n"
                    "CRITICAL: The following names and roles are LOCKED. You MUST use them. DO NOT CHANGE or DEVIATE from them.\n"
                    + "\n".join(anchors)
                    + "\n---\n"
                )

        # *** NEW: Prepare Prose Bridge from previous beat ***
        prose_bridge_text = ""
        if previous_beat_prose:
            last_words = previous_beat_prose.split()[-200:]
            prose_bridge_text = (
                "**[PREVIOUS SCENE EXCERPT (FOR PROSE CONTINUITY)]**\n"
                "The last scene ended like this. Continue the story fluidly from this point, matching tone and syntax.\n"
                "---\n"
                f"...{' '.join(last_words)}...\n"
                "---\n"
            )

        # Format all state components for the prompt
        character_manifest = json.dumps(char_stances, indent=2)
        ledger_facts = json.dumps(narrative_ledger, indent=2)
        world_facts = json.dumps(world_bible, indent=2)
        baton_context = json.dumps(narrative_baton, indent=2)

        # 2. INJECT: Construct the prompt for this specific beat
        prompt = f"""
        You are a Master Storyteller. Your task is to write a single narrative beat based on a specific instruction.

        {character_anchor_text}

        **[BACKGROUND CONTEXT (DO NOT REPEAT)]**
        This is the ground truth. Do not contradict it, but do not summarize it.
        - World Bible (Immutable): {world_facts}
        - Character Manifest: {character_manifest}
        - Narrative Ledger (Current State): {ledger_facts}
        ---

        **[NARRATIVE BATON]**
        This is the immediate prequel to your scene. Ensure a seamless transition from this point.
        {baton_context}
        ---
        
        {prose_bridge_text}

        **[INSTRUCTION FOR THIS BEAT]**
        Your goal is to write the scene for: "{beat_instruction}"
        ---

        **[STYLE DNA]**
        Mimic this Narrator Voice: {epoch_style_desc}
        
        **[USER CADENCE REFERENCE]**
        Follow this rhythmic pattern: {user_style_context}
        ---

        **INSTRUCTIONS:**
        1.  **Write the Scene:** Write a short scene (approx 200-300 words) that fulfills the [INSTRUCTION FOR THIS BEAT].
        2.  **MEDIA RES:** Start the action immediately. Do NOT summarize previous events. Do NOT explain the backstory.
        3.  **Adhere to State:** Your output MUST be consistent with the World Bible, Character Manifest, and Narrative Ledger.
        4.  **Maintain Cohesion:** Use the [NARRATIVE BATON] and [PREVIOUS SCENE EXCERPT] to ensure a smooth narrative, tonal, and conversational transition.

        Format:
        [VISUAL]: Description
        (VOICEOVER): Text...

        BEGIN BEAT:
        """
        
        # 3. RENDER: Generate the beat
        draft_beat = self.llm.chat_completion(prompt)

        # 4. VALIDATE: Run the hard and soft checks
        self._check_compliance_hard(draft_beat, world_bible)

        logger.info("    entering The Cage for atomic beat...")
        # *** FIX: Use user_style_context instead of undefined style_context ***
        review_result = self.cage.review_draft(
            volume_id=volume_id,
            node_id=f"atomic_beat_{uuid.uuid4()}",
            draft_text=draft_beat,
            user_context=f"Style: {user_style_context[:100]}", 
            domain_context=universe_anchor,
            prohibitions=prohibitions,
            character_stances=char_stances,
            narrative_intent=beat_instruction
        )

        if review_result.status != ReviewStatus.PASS:
            logger.warning(f"      Beat failed soft review: {review_result.issues}. Suggestion: {review_result.suggestion}")
            raise RuntimeError(f"Soft compliance fail: {review_result.issues}")

        logger.info("      Beat Passed All Checks.")
        return draft_beat, review_result.model_dump()

    # *** MODIFIED: Looping logic for Prose Bridge ***
    def _phase_drafting(self, trailhead: Dict, outline: str, research_atoms: List[Dict], user_id: str, volume_id: str) -> str:
        logger.info("  ✍️ Phase 3: Commencing Atomic Beat Loop Drafting...")

        # 1. Deconstruct outline into atomic beats
        outline_parser_prompt = f"""
        Given the following script outline, break it down into a JSON array of distinct narrative beats.
        Each beat should be a single, focused scene or event.
        The output should be a JSON array of strings. Example: ["The hero enters the cave.", "She finds the glowing sword.", "A dragon awakens."]

        Outline:
        ---
        {outline}
        ---

        JSON Array Output:
        """
        try:
            response = self.llm.chat_completion(outline_parser_prompt)
            cleaned_response = response.strip().replace('`', '').replace('json', '')
            atomic_beats = json.loads(cleaned_response)
        except Exception as e:
            logger.error(f"Failed to parse outline into atomic beats: {e}. Falling back to line-by-line split.")
            atomic_beats = [beat.strip() for beat in outline.split('\n') if beat.strip() and beat.strip().startswith("##")]

        # 2. The Atomic Loop
        final_script_segments = []
        previous_beat_text = "" # NEW: For prose bridge
        narrative_baton = {
            "last_speaker": "Narrator",
            "emotional_tone": "neutral",
            "open_loop": "The story is about to begin."
        }
        max_attempts_per_beat = 3

        for i, beat_instruction in enumerate(atomic_beats):
            self._report("Drafting", 80 + int((i / len(atomic_beats)) * 15), f"Generating Beat {i+1}/{len(atomic_beats)}: {beat_instruction[:40]}...")
            logger.info(f"    [Beat {i+1}/{len(atomic_beats)}] Instruction: {beat_instruction}")
            
            generated_beat = None
            for attempt in range(max_attempts_per_beat):
                logger.info(f"      Attempt {attempt + 1}/{max_attempts_per_beat} for beat {i+1}...")
                try:
                    generated_beat_text, review_result = self._generate_atomic_beat(
                        volume_id=volume_id,
                        user_id=user_id,
                        beat_instruction=beat_instruction,
                        narrative_baton=narrative_baton,
                        previous_beat_prose=previous_beat_text # NEW: Pass previous prose
                    )
                    
                    self._update_narrative_ledger(volume_id, generated_beat_text)
                    narrative_baton = self._summarize_beat_for_baton(generated_beat_text)
                    
                    generated_beat = generated_beat_text
                    previous_beat_text = generated_beat_text # NEW: Update for next loop
                    break

                except (ValueError, RuntimeError) as e:
                    logger.warning(f"      Validation Fail on Beat {i+1}, Attempt {attempt+1}: {e}. Retrying...")
                except Exception as e:
                    logger.error(f"      Critical Error generating beat {i+1}, Attempt {attempt+1}: {e}")

            if not generated_beat:
                raise ValueError(f"Failed to generate and validate narrative beat '{beat_instruction}' after {max_attempts_per_beat} attempts.")

            final_script_segments.append(f"## {beat_instruction}\n\n{generated_beat}")

        full_script = "\n\n".join(final_script_segments)
        logger.info("  Atomic Beat Loop Completed.")

        final_review_summary = {"status": "PASS", "details": "All atomic beats passed validation."}
        
        return full_script, final_review_summary
