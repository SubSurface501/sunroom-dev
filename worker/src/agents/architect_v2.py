import logging
import json
import uuid
import random
import re
import traceback
import difflib
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from .base import BaseAgent
from prompts import VOLUME_ARCHITECT_PROMPT, ARCHITECT_GROWTH_PROMPT, VOLUME_PLANNER_PROMPT, DIRECTED_GROWTH_PROMPT, ACTION_CHAIN_PROMPT, PHYSICS_PARSER_PROMPT
from db import crud, schemas
from .energy_middleware import EnergyModelMiddleware
from .domain_expert import DomainExpertAgent
from worker.src.services.context_engine import ContextEngine
from worker.src.simulation.actions import ActionType, MoveAction, TakeAction, InspectAction, SpeakAction, AttackAction, UseAction, DropAction
from worker.src.simulation.engine import PhysicsEngine
from worker.src.simulation.procedural import ProceduralGenerator
from worker.src.context_frame import NarrativeLedger, HardState, WorldBible, Entity, EntityType, WorldLaw
# Use local schemas for WorldLaw if needed, but context_frame defines the Pydantic model. 
# In _grow_linear_beat we used 'schemas.WorldLaw'. 
# Let's fix that usage to use the imported WorldLaw from context_frame or alias it.
# The cleanest way is to just use WorldLaw directly since we imported it.


logger = logging.getLogger(__name__)


class StoryNodeSchema(BaseModel):
    title: str = Field(..., description="The concept name or scene title")
    summary: str = Field(..., description="A 2-sentence summary of the event")

class LinearBeatResultSchema(BaseModel):
    choice_label: str = Field(..., description="The action taken to reach this beat")
    child_title: str = Field(..., description="The title of the new scene")
    child_summary: str = Field(..., description="A summary of the new scene")

class VolumeArchitectAgent(BaseAgent):
    """
    The Deep Weaver.
    Generates a StoryVolume by iteratively growing a linear narrative chain.
    Ensures perfect continuity for multi-epoch sagas.
    """
    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        self.volume_root_concept = None # To store the root concept for consistent context
        self.constraints = {} # Store constraints for the current volume
        
        # Try to initialize but don't crash if Redis is down
        try:
            self.energy_middleware = EnergyModelMiddleware()
        except Exception as e:
            logger.warning(f"EnergyModelMiddleware failed to load ({e}). Novelty scoring disabled.")
            self.energy_middleware = None

        self.domain_expert = DomainExpertAgent(db, worker, llm)
        
        try:
            self.context_engine = ContextEngine(db)
        except Exception as e:
            logger.warning(f"ContextEngine failed to load ({e}). Memory context disabled.")
            self.context_engine = None

    def _parse_physics_tags(self, seed_prose: str) -> Dict[str, Any]:
        """
        Extracts Physics Laws and State from Seed Prose using a Hybrid (Regex + LLM) approach.
        """
        logger.info("Parsing Physics Tags from Seed Prose...")
        
        # 1. Pass 1: Explicit Regex Overrides
        explicit_laws = re.findall(r"\[LAW:\s*(.*?)\]", seed_prose)
        explicit_start = re.search(r"\[START:\s*(.*?)\]", seed_prose)
        
        # 2. Pass 2: LLM Inference
        prompt = PHYSICS_PARSER_PROMPT.format(seed_prose=seed_prose)
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            manifest = self._parse_json(resp)
        except Exception as e:
            logger.error(f"Physics parsing failed: {e}")
            manifest = {}

        # 3. Merge & Override
        if explicit_laws:
            manifest.setdefault("detected_laws", []).extend(explicit_laws)
        
        if explicit_start:
            manifest.setdefault("starting_ledger", {})["location"] = explicit_start.group(1).strip()

        # 4. Normalize
        if not manifest.get("starting_ledger"):
            manifest["starting_ledger"] = {"location": "loc_unknown", "inventory": []}
            
        logger.info(f"Physics Calibration Complete: {json.dumps(manifest, indent=2)}")
        return manifest

    def _load_bible_and_state(self, universe_id: str, epoch_id: int) -> Tuple[WorldBible, NarrativeLedger]:
        """Loads the simulation context from the database."""
        # 1. Load Bible from Universe
        bible = WorldBible(world_seed=f"seed_{universe_id or 'default'}")
        
        if universe_id:
            try:
                res = self.db.table("Universes").select("world_bible").eq("id", universe_id).single().execute()
                if res.data and res.data.get('world_bible'):
                    wb_data = res.data['world_bible']
                    
                    # Map Entities
                    if "entities" in wb_data:
                        for ent_id, ent_data in wb_data["entities"].items():
                            bible.entities[ent_id] = Entity(
                                name=ent_data.get('name', ent_id),
                                type=EntityType.CHARACTER if "role" in ent_data else EntityType.OBJECT,
                                description=ent_data.get('description', ''),
                                immutable_traits=ent_data.get('traits', []),
                                location_id=ent_data.get('location_id', 'loc_unknown'),
                                price=ent_data.get('price', 0)
                            )
                    
                    # Map Laws
                    if "laws" in wb_data:
                        for law in wb_data["laws"]:
                             if isinstance(law, dict):
                                 bible.laws.append(WorldLaw(**law))
                             else:
                                 bible.laws.append(WorldLaw(name=str(law), description="Manifest Law"))
                
                logger.info(f"Loaded World Bible for Simulation: {len(bible.entities)} entities.")
            except Exception as e:
                logger.warning(f"Failed to load Bible from DB: {e}. Using empty bible.")

        # 2. Load Ledger (or create fresh)
        ledger = NarrativeLedger()
        if epoch_id:
             try:
                 ep_res = self.db.table("Epochs").select("narrative_ledger").eq("id", epoch_id).single().execute()
                 if ep_res.data and ep_res.data.get('narrative_ledger'):
                     # Safe load into Pydantic model
                     raw_ledger = ep_res.data['narrative_ledger']
                     if isinstance(raw_ledger, dict):
                         # If it's a list, we might need to handle legacy but usually it's a dict for V8
                         # Simple direct mapping for MVP, more robust mapping might be needed
                         ledger = NarrativeLedger(**raw_ledger)
                         logger.info(f"Loaded Narrative Ledger for Simulation. Location: {ledger.hard_state.current_location_id}")
             except Exception as e:
                 logger.warning(f"Failed to load Ledger from DB: {e}")
             
        return bible, ledger

    def _plan_action_chain(self, objective: str, ledger: NarrativeLedger, bible: WorldBible, latent_entities: List[str] = None, error_feedback: str = None) -> List[Dict]:
        """
        Asks the LLM to generate a chain of physical actions.
        Now includes VIRTUAL VISION (Procedural Inventory) so the Architect can see shop items.
        """
        current_loc = ledger.hard_state.current_location_id
        
        # 1. Standard Bible Entities
        local_entities = [
            f"{ent.name} ({ent_id})" for ent_id, ent in bible.entities.items() 
            if ent.location_id == current_loc
        ]
        
        # 2. Virtual Vision (Procedural Inventory)
        # If the Architect is in a shop/location, let it see the procedural stock.
        try:
            # We assume the world seed is consistent (e.g., 'seed_universe_id')
            # Since we don't pass the seed here explicitly, we use a hash of the location for deterministic procedural gen
            # or rely on the bible's seed if available.
            seed = bible.world_seed or f"seed_{current_loc}"
            proc_gen = ProceduralGenerator(seed, bible=bible)
            virtual_items = proc_gen.generate_virtual_inventory(current_loc)
            
            for item_name in virtual_items:
                # Add to local entities so the Planner sees them
                # Format: "Rope (item_rope_virtual)"
                item_id = f"item_{item_name.lower().replace(' ', '_')}_virtual"
                local_entities.append(f"{item_name} ({item_id}) [Virtual Stock]")
                
                # CRITICAL: We must also inject them into the Bible TEMPORARILY so the Physics Engine accepts the 'Take' action
                if item_id not in bible.entities:
                    bible.entities[item_id] = Entity(
                        name=item_name,
                        type=EntityType.OBJECT,
                        description="A procedural item.",
                        immutable_traits=[],
                        location_id=current_loc,
                        price=10 # Default price
                    )
        except Exception as e:
            logger.warning(f"Virtual Vision failed: {e}")

        # --- V10.1 FIX: Inject World Laws into Planner Prompt ---
        laws_str = "No specific laws defined."
        if bible.laws:
            laws_str = "\n".join([f"- {law.name}: {law.description}" for law in bible.laws])
        # --- END FIX ---

        prompt = ACTION_CHAIN_PROMPT.format(
            objective=objective + (f"\n\nPREVIOUS PLAN FAILED: {error_feedback}" if error_feedback else ""),
            world_laws=laws_str,
            location=current_loc,
            inventory=ledger.hard_state.inventory,
            entities=", ".join(local_entities) or "None visible"
        )
        
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            # Basic cleaning
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            
            return json.loads(resp.strip())
        except Exception as e:
            logger.error(f"Action planning failed: {e}")
            return []

    def _grow_linear_beat(self, parent: Dict, topic: str, current_depth: int, target_depth: int, lenses: List[str] = None, time_range: Dict = None, project_id: str = None, user_id: str = None, all_nodes: List[Dict] = None, all_connections: List[Dict] = None, archetype: str = None, prohibitions: List[str] = None, epoch_id: int = None, character_stances: Dict = None, narrative_ledger: List[str] = None, universe_id: str = None, current_objective: str = None, physics_manifest: Dict = None, in_memory_ledger: Optional[Dict] = None) -> Dict:
        """
        V8 UPDATE: The Simulation Loop.
        Instead of writing a summary, we Plan -> Simulate -> Commit.
        """
        
        # 1. Initialize Physics
        bible, db_ledger = self._load_bible_and_state(universe_id, epoch_id)
        current_ledger = db_ledger
        if in_memory_ledger:
            try:
                current_ledger = NarrativeLedger(**in_memory_ledger)
                logger.info(f"Loaded in-memory ledger for simulation continuity. Location: {current_ledger.hard_state.current_location_id}")
            except Exception as e:
                logger.warning(f"Failed to load in-memory ledger, falling back to DB state. Error: {e}")
        
        # --- V8 DYNAMIC POPULATION ---
        # Inject parsed entities into the Bible so the engine knows about them
        if physics_manifest and "entities" in physics_manifest:
             for ent in physics_manifest["entities"]:
                 # Map JSON to Entity Object
                 try:
                     entity_obj = Entity(
                        name=ent.get("name", "Unknown Item"),
                        type=EntityType.OBJECT, # Default to object for now
                        description=ent.get("description", "A manifest item."),
                        immutable_traits=ent.get("traits", []),
                        location_id=ent.get("location_id"),
                        price=0
                     )
                     bible.entities[ent.get("id")] = entity_obj
                 except Exception as e:
                     logger.warning(f"Failed to inject manifest entity {ent}: {e}")

        # Inject detected laws
        if physics_manifest and "laws" in physics_manifest:
             for law_name in physics_manifest["laws"]:
                 # Simple law injection
                 bible.laws.append(WorldLaw(name=law_name, description="Parsed from Seed Prose", consequences="Unknown"))
        
        # --- V14.9 LOGIC BATON PASS ---
        # 1. Take the rules compiled during the initial Calibration
        if physics_manifest and "volume_logic" in physics_manifest:
            # 2. Force them into the bible for the CURRENT beat's simulation
            bible.dynamic_rules = physics_manifest["volume_logic"]
            logger.info(f"Wired {len(bible.dynamic_rules)} dynamic logic rules into the World Bible.")

        # 3. Do the same for the Thematic Template (Shop items)
        if physics_manifest and "thematic_template" in physics_manifest:
            bible.thematic_template = physics_manifest["thematic_template"]
            logger.info("Wired AI-generated thematic template into the World Bible.")
                 
        # --- V8 LEDGER HYDRATION ---
        # Ensure the simulation starts with items the Parser identified as "already possessed"
        if physics_manifest and "starting_ledger" in physics_manifest:
            starting_inv = physics_manifest["starting_ledger"].get("inventory", [])
            if starting_inv:
                # Add items if they aren't already there
                for item in starting_inv:
                    if item not in current_ledger.hard_state.inventory:
                        current_ledger.hard_state.inventory.append(item)
                logger.info(f"Hydrated Simulation Inventory from Manifest: {current_ledger.hard_state.inventory}")

        engine = PhysicsEngine(bible)
        
        # 2. Simulation Loop (Try 3 times to get a valid plan)
        simulation_trace = []
        final_ledger = current_ledger
        
        error_msg = None
        
        for attempt in range(3):
            # A. Plan
            latent_entities = physics_manifest.get('latent_entities', [])
            action_plan_data = self._plan_action_chain(
                objective=current_objective, 
                ledger=current_ledger,
                bible=bible, # <--- PASS BIBLE HERE
                latent_entities=latent_entities, 
                error_feedback=error_msg
            )
            if not action_plan_data:
                continue
                
            # B. Simulate
            temp_ledger = current_ledger.model_copy(deep=True)
            trace = []
            failed = False
            
            for action_data in action_plan_data:
                # Convert dict to Pydantic Action (Simple factory for MVP)
                try:
                    action_type = action_data.get('action_type')
                    # We need to map strings to classes dynamically or use a big if/else
                    # For MVP speed, we'll do a quick lookup
                    from worker.src.simulation.actions import MoveAction, TakeAction, InspectAction, SpeakAction, AttackAction, UseAction, DropAction
                    cls_map = {
                        "move": MoveAction, "take": TakeAction, "inspect": InspectAction,
                        "speak": SpeakAction, "attack": AttackAction, "use": UseAction, "drop": DropAction
                    }
                    if action_type not in cls_map: continue
                    
                    action_obj = cls_map[action_type](**action_data)
                    
                    # EXECUTE
                    temp_ledger, result = engine.execute_action(temp_ledger, action_obj)
                    
                    if not result.success:
                        failed = True
                        error_msg = f"Action '{action_type}' failed: {result.message}"
                        logger.warning(f"Simulation Fail: {error_msg}")
                        break
                    
                    trace.append({
                        "action": action_data,
                        "result": result.dict()
                    })
                    
                except Exception as e:
                    failed = True
                    error_msg = f"Invalid Action Format: {e}"
                    break
            
            if not failed:
                # Success!
                simulation_trace = trace
                final_ledger = temp_ledger
                break
        
        if not simulation_trace:
            logger.error("Failed to generate valid action chain after 3 attempts.")
            return None

        # 3. Generate "Summary" for compatibility (The Writer will use the Trace, but Graph needs a title)
        # --- V10.2 SUMMARY ISOLATION ---
        # Derive the summary from what HAPPENED, not from the objective.
        summary_prompt = f"""
        Summarize the following sequence of events from a text-based RPG into a single, past-tense sentence.
        Do not mention the character's name. Start with a verb.
        
        TRACE:
        {json.dumps(simulation_trace, indent=2)}
        
        SUMMARY:
        """
        try:
            # Use a fast, cheap model for this simple task
            post_hoc_summary = self.llm.chat_completion(summary_prompt, model="gemini-2.0-flash-exp", json_schema=None).strip()
        except Exception as e:
            # V12.1: Deterministic Fallback
            # Join all the 'message' fields from the trace results
            trace_recap = " ".join([s.get('result', {}).get('message', '') for s in simulation_trace])
            post_hoc_summary = trace_recap or "The character performed actions in the environment."
            logger.warning(f"Post-hoc summary generation failed ({e}). Using deterministic trace recap: {post_hoc_summary}")
        # --- END FIX ---
        
        # Return the data structure expected by the caller, but enriched with V8 data
        return {
            "choice_label": "Continue", # Default for linear
            "child_title": current_objective[:50], # Use objective as title
            "child_summary": post_hoc_summary, # Placeholder, Writer uses Trace
            "novelty_score": 0.8,
            "simulation_trace": simulation_trace, # <--- THE GOLD
            "resulting_state": final_ledger.dict()
        }

    def _refine_seed_prose(self, raw_prose: str, previous_context: str = None, character_anchors: str = "") -> str:
        """
        Translates raw user prose into a machine-ready structured format.
        Now Identity-Aware: Prevents name-drifting by enforcing character anchors.
        """
        if not raw_prose: return raw_prose

        logger.info("Refining Seed Prose into System Directives...")
        
        context_block = ""
        if previous_context:
            context_block = f"**PREVIOUS CHAPTER ENDING (ESTABLISHED REALITY):**\n{previous_context}\n\n**CONSTRAINT:** Your directives MUST logically follow this ending. If the Raw Prose contradicts the established reality (e.g. location, injury), you must ADAPT the directives to bridge the gap."

        anchor_block = ""
        if character_anchors:
            anchor_block = f"**CANONICAL IDENTITY ANCHORS (INVIOLABLE):**\n{character_anchors}\n*CRITICAL: You MUST use these names and roles. Do not invent new names or aliases.*\n"

        prompt = f"""
        You are a Narrative Engineer. Your job is to convert raw, messy author notes into a rigid set of Machine Directives.
        
        {anchor_block}

        {context_block}
        
        **RAW USER PROSE (Target Scene):**
        "{raw_prose}"
        
        **TASK:**
        Rewrite this into the following strict format:
        
        [GOAL]: The singular objective of this chapter.
        [STARTING_STATE]: The EXACT physical condition/location where the scene BEGINS.
        [CONTEXT]: The physical setting and immediate situation at the start.
        [ACTION]: The specific actions the character must take across the chapter.
        [CRITICAL INSTRUCTION]: A mandatory plot beat that MUST happen.
        [ENDING STATE]: The EXACT physical condition/location where the scene STOPS.
        
        **RULES:**
        1.  **NO AMBIGUITY:** Use specific, concrete nouns.
        2.  **HARD STOP:** The [ENDING STATE] must be a definitive cut-off point.
        3.  **IDENTITY LOCK:** You MUST use the names provided in the CANONICAL IDENTITY ANCHORS. Do not deviate.
        4.  **CONTINUITY:** Bridge the gap with the PREVIOUS CHAPTER ENDING.
        
        **OUTPUT:**
        Return ONLY the formatted text.
        """
        
        try:
            refined_prose = self.llm.chat_completion(prompt, json_schema=None)
            logger.info(f"Refined Prose:\n{refined_prose}")
            return refined_prose
        except Exception as e:
            logger.error(f"Failed to refine prose: {e}")
            return raw_prose

    def _ensure_volume_and_branch(self, user_id: str, topic: str, project_id: str = None, volume_id: str = None, universe_id: str = None, storyline_id: str = None) -> tuple[str, str]:
        # 1. Ensure Volume
        if not volume_id:
             # Try to find existing
             res = self.db.table("StoryVolumes").select("id").eq("root_concept", topic).eq("user_id", user_id).limit(1).execute()
             if res.data:
                 volume_id = res.data[0]['id']
             else:
                 vol_data = {
                    "user_id": user_id,
                    "title": topic,
                    "root_concept": topic,
                    "status": "drafting",
                    "project_id": project_id,
                    "universe_id": universe_id,
                    "storyline_id": storyline_id
                 }
                 res = self.db.table("StoryVolumes").insert(vol_data).execute()
                 volume_id = res.data[0]['id']
        
        # 2. Ensure Main Branch
        main_branch = None
        branches = crud.get_branches_for_volume(self.db, volume_id)
        for b in branches:
            if b.name == "main":
                main_branch = b
                break
        
        if not main_branch:
            main_branch = crud.create_branch(self.db, schemas.BranchCreate(volume_id=volume_id, name="main", is_active=True))
            
        return volume_id, main_branch.id

    def _persist_nodes(self, volume_id: str, branch_id: str, nodes_data: List[Dict], id_map: Dict) -> Dict:
        """Persists a batch of nodes and updates the id_map."""
        new_map = id_map.copy()
        for n in nodes_data:
            # Check if already persisted (e.g. root node might be processed specially)
            if n['node_id'] in new_map: continue
            
            # Ensure context_snapshot is a string (JSON dump if it's a dict)
            context_snapshot_data = n.get('context_snapshot', '')
            if isinstance(context_snapshot_data, dict):
                context_snapshot_str = json.dumps(context_snapshot_data)
            else:
                context_snapshot_str = str(context_snapshot_data)
            
            node_create = schemas.NodeCreate(
                volume_id=volume_id,
                branch_id=branch_id,
                title=n['title'],
                type=n['type'],
                content=n.get('content', {}),
                context_snapshot=context_snapshot_str,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db_node = crud.create_node(self.db, node_create)
            new_map[n['node_id']] = db_node.id
            logger.debug(f"Persisted Node: {db_node.id}")
            
        return new_map

    def _persist_connections(self, volume_id: str, connections: List[Dict], id_map: Dict):
        for c in connections:
            source_id = id_map.get(c['from'])
            target_id = id_map.get(c['to'])
            
            if source_id and target_id:
                try:
                    edge_create = schemas.EdgeCreate(
                        volume_id=volume_id,
                        source_node_id=source_id,
                        target_node_id=target_id,
                        type=c.get('joint_type', 'direct'),
                        label=c.get('choice_label'),
                        created_at=datetime.now(timezone.utc)
                    )
                    crud.create_edge(self.db, edge_create)
                except Exception as e:
                    logger.warning(f"Edge creation failed (likely duplicate): {e}")

    def _get_previous_volume_context(self, storyline_id: str, current_volume_id: str) -> str:
        """
        Fetches the narrative ending of the IMMEDIATELY PRECEDING volume in this storyline.
        Acts as the 'Baton Pass' for continuity.
        """
        if not storyline_id:
            return "No previous context (First Chapter)."
            
        try:
            # 1. Find the previous volume (latest one that isn't this one)
            # We assume creation order implies narrative order for now.
            res = self.db.table("StoryVolumes") \
                .select("id, title") \
                .eq("storyline_id", storyline_id) \
                .neq("id", current_volume_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if not res.data:
                return "No previous context (First Chapter)."
            
            prev_vol = res.data[0]
            logger.info(f"🔗 Linking to previous volume: {prev_vol['title']} ({prev_vol['id']})")
            
            # 2. Find the Final Node of that volume (Climax)
            # We look for type='climax' or the latest created node.
            node_res = self.db.table("Nodes") \
                .select("content") \
                .eq("volume_id", prev_vol['id']) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
                
            if not node_res.data:
                return f"Previous volume '{prev_vol['title']}' exists but has no nodes."
                
            last_node_content = node_res.data[0].get('content', {})
            pages = last_node_content.get('pages', [])
            
            if pages:
                last_text = pages[-1].get('narrative_text', '')
                return f"PREVIOUS CHAPTER ENDED WITH:\n...{last_text[-500:]}"
            else:
                return f"Previous volume '{prev_vol['title']}' ended with summary: {last_node_content.get('summary', '')}"

        except Exception as e:
            logger.error(f"Failed to fetch previous context: {e}")
            return "Error retrieving previous context."

    def plan_volume(self, seed_prose: str, previous_context: str, knowledge_horizon: str, termination_condition: str, depth: int) -> List[Dict]:
        """
        Decomposes the seed prose into a linear sequence of atomic objectives.
        Returns a list of dicts: [{'objective': '...', 'local_termination': '...'}]
        """
        logger.info("Planner: Decomposing Volume into Atomic Objectives...")
        from prompts import VOLUME_PLANNER_PROMPT
        
        prompt = VOLUME_PLANNER_PROMPT.format(
            root_concept=seed_prose,
            previous_context=previous_context or "None.",
            termination_condition=termination_condition,
            knowledge_horizon=knowledge_horizon,
            depth=depth
        )
        
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            data = self._parse_json(resp)
            plan = data.get("plan", [])
            
            # Validation
            if not isinstance(plan, list) or not plan:
                logger.warning("Planner returned invalid format. Fallback to single objective.")
                return [{"objective": seed_prose, "local_termination": termination_condition}]
            
            # Normalize strings to dicts (backward compatibility)
            normalized_plan = []
            for item in plan:
                if isinstance(item, str):
                    normalized_plan.append({"objective": item, "local_termination": "End of scene."})
                else:
                    normalized_plan.append(item)
            
            # Log
            log_str = "\n".join([f"{i+1}. {step.get('objective')} (Stop: {step.get('local_termination')})" for i, step in enumerate(normalized_plan)])
            logger.info(f"Planner Generated {len(normalized_plan)} Steps:\n{log_str}")
            
            return normalized_plan
        except Exception as e:
            logger.error(f"Planner failed: {e}")
            return [{"objective": seed_prose, "local_termination": termination_condition}]

    def run_task(self, user_id: str, topic: str, depth: int = 12, lenses: List[str] = None, seed_prose: str = None, time_range: Dict = None, project_id: str = None, volume_id: str = None, universe_id: str = None, storyline_id: str = None):
        logger.info(f"Designing Linear Volume: {topic} (Depth: {depth}, Lenses: {lenses}, Project: {project_id}, VolumeID: {volume_id})")

        # Store the initial root concept
        self.volume_root_concept = topic 

        # 0. Setup Volume & Branch
        volume_id, main_branch_id = self._ensure_volume_and_branch(user_id, topic, project_id, volume_id, universe_id, storyline_id)
        node_id_map = {} # Maps temp_id -> db_uuid

        # --- PRE-FLIGHT CHECK: Derive Constraints ---
        # We do this once at the start so all nodes share the same boundaries.
        effective_seed_prose = seed_prose
        
        # --- ONTOLOGY CHECK (Universe/Epoch) ---
        archetype = None
        prohibitions = []
        epoch_id = None
        db_seed_prose = None
        character_stances = {}
        narrative_ledger = []
        world_bible_data = {}
        
        if universe_id:
            try:
                # Get Active Epoch ID and World Bible
                uni_res = self.db.table("Universes").select("active_epoch_id, world_bible").eq("id", universe_id).single().execute()
                if uni_res.data:
                    world_bible_data = uni_res.data.get('world_bible', {})
                    if uni_res.data.get('active_epoch_id'):
                        epoch_id = uni_res.data['active_epoch_id']
                        # Get Epoch Details
                        ep_res = self.db.table("Epochs").select("archetype, prohibitions, seed_prose, character_stances, narrative_ledger").eq("id", epoch_id).single().execute()
                        if ep_res.data:
                            archetype = ep_res.data.get('archetype')
                            prohibitions = ep_res.data.get('prohibitions', [])
                            db_seed_prose = ep_res.data.get('seed_prose')
                            character_stances = ep_res.data.get('character_stances', {})
                            narrative_ledger = ep_res.data.get('narrative_ledger', [])

                            # --- AUTO-SOUL INJECTION ---
                            if not character_stances and db_seed_prose:
                                logger.info("👻 Character Soul Empty. Injecting Soul from Seed Prose...")
                                try:
                                    soul_prompt = f"""
                                    Analyze the following Seed Prose for a story epoch.
                                    Extract the primary character(s) and their current psychological stance/mood/belief system based on this text.
                                    Return strictly valid JSON: {{ "Character Name": "Psychological Profile/Stance" }}
                                    
                                    SEED PROSE:
                                    "{db_seed_prose}"
                                    """
                                    soul_resp = self.llm.chat_completion(soul_prompt, json_schema=None)
                                    injected_stances = self._parse_json(soul_resp)
                                    
                                    if injected_stances and isinstance(injected_stances, dict):
                                        character_stances = injected_stances
                                        self.db.table("Epochs").update({"character_stances": character_stances}).eq("id", epoch_id).execute()
                                        logger.info(f"Auto-Soul Injection Complete: {character_stances}")
                                except Exception as e:
                                    logger.error(f"Auto-Soul Injection Failed: {e}")

                            logger.info(f"🔮 Architect locked to Epoch {epoch_id} | Archetype: {archetype}")
            except Exception as e:
                logger.warning(f"Failed to fetch Universe/Epoch details: {e}")

        # Use passed seed_prose if available, otherwise fallback to DB persistent one
        raw_seed_prose = seed_prose if seed_prose else db_seed_prose
        
        # --- BATON PASS: Get Previous Context ---
        previous_context = self._get_previous_volume_context(storyline_id, volume_id)

        # --- V8.5 IDENTITY ANCHOR CONSTRUCTION ---
        character_anchors = ""
        if world_bible_data and "entities" in world_bible_data:
            anchors = []
            for key, entity in world_bible_data["entities"].items():
                if "name" in entity:
                    role = entity.get('role', 'Character')
                    anchors.append(f"- {entity['name']}: {role}.")
            if anchors:
                character_anchors = "\n".join(anchors)

        # --- THE REFINER: Translate Raw Prose to Machine Directives ---
        # V8.5 Fix: Inject Identity Anchors
        final_seed_prose = self._refine_seed_prose(raw_seed_prose, previous_context, character_anchors=character_anchors)
        
        # --- V8 CALIBRATION: Parse Physics & State ---
        physics_manifest = self._parse_physics_tags(final_seed_prose)
        
        # Use the manifest to configure the initial constraints
        self.constraints = self._derive_constraints(final_seed_prose)
        
        # Merge Parser results into constraints for the Planner
        ledger_data = physics_manifest.get("starting_ledger")
        if ledger_data and isinstance(ledger_data, dict) and ledger_data.get("location"):
             self.constraints["start_location"] = ledger_data["location"]
        
        logger.info(f"Derived Constraints: {self.constraints}")

        # --- V4 UPGRADE: THE PLANNER ---
        # Instead of generic iterative growth, we Plan the Route.
        termination_condition = self.constraints.get("termination_condition", "End of Chapter")
        knowledge_horizon = self.constraints.get("knowledge_horizon", "Local knowledge only.")
        
        plan = self.plan_volume(final_seed_prose, previous_context, knowledge_horizon, termination_condition, depth)
        
        # 1. Generate Root Node (Step 1 of Plan)
        root_step = plan[0]
        root_objective = root_step.get("objective", "Start Story")
        root_termination = root_step.get("local_termination", termination_condition)
        
        remaining_plan = plan[1:]
        
        root_node_data = self._generate_root(topic, lenses, time_range, project_id, user_id, root_objective, archetype, prohibitions, character_stances, narrative_ledger, depth, previous_context, termination_condition=root_termination, physics_manifest=physics_manifest)
        if not root_node_data:
            return None

        # PERSIST ROOT NODE
        node_id_map = self._persist_nodes(volume_id, main_branch_id, [root_node_data], node_id_map)
        
        nodes = [root_node_data] 
        connections = [] 
        
        # 2. Growth Loop (Directed by Plan)
        current_node = root_node_data
        in_memory_ledger = None # Initialize in-memory ledger
        
        # Iterate strictly through the remaining plan
        for i, step in enumerate(remaining_plan):
            step_num = i + 2 # Since Root was Step 1
            objective = step.get("objective")
            local_termination = step.get("local_termination", termination_condition)
            
            logger.info(f"Growing Directed Beat {step_num}/{len(plan)}: {objective[:40]}... (Stop: {local_termination[:30]})")
            
            # --- V8.5 RELIABILITY PATCH: Retry Loop ---
            beat_data = None
            for retry_idx in range(3):
                beat_data = self._grow_linear_beat(
                    current_node, topic, step_num, len(plan), lenses, time_range, 
                    project_id, user_id, nodes, connections, archetype, prohibitions, 
                    epoch_id, character_stances, narrative_ledger, universe_id=universe_id,
                    current_objective=objective,
                    physics_manifest=physics_manifest,
                    in_memory_ledger=in_memory_ledger # Pass the ledger state
                )
                if beat_data:
                    break
                logger.warning(f"Beat {step_num} failed generation (Attempt {retry_idx+1}/3). Retrying...")
            
            child_id = f"node_{uuid.uuid4().hex[:8]}" # Generate ID once

            # --- V8.5 Fix: Inject Local Termination into Content Constraints ---
            node_constraints = self.constraints.copy()
            node_constraints["termination_condition"] = local_termination
            
            if not beat_data:
                logger.error(f"FATAL: Beat {step_num} failed generation after 3 retries. Creating a placeholder error node.")
                child_node_data = {
                    "node_id": child_id,
                    "title": f"ERROR: Failed to plan Scene {step_num}",
                    "type": "error",
                    "content": {
                        "summary": f"The Architect failed to generate a valid plan for this scene after multiple attempts due to physics or logical constraints.",
                        "error_message": f"Failed to plan action chain for objective: {objective}",
                        "objective": objective,
                        "constraints": node_constraints,
                        "choice_label": "Error: Planning Failed"
                    },
                    "context_snapshot": json.dumps(in_memory_ledger) if in_memory_ledger else "" # Snapshot of state *before* this failed beat
                }
                # Do NOT update in_memory_ledger if the beat failed, carry forward the previous successful state.
            else:
                child_node_data = {
                    "node_id": child_id,
                    "title": beat_data.get("child_title", "Untitled"),
                    "type": "climax" if i == len(remaining_plan) - 1 else "branch",
                    "content": {
                        "summary": beat_data.get("child_summary", ""), 
                        "novelty_score": beat_data.get("novelty_score", 0.5),
                        "choice_label": beat_data.get("choice_label", "Next"),
                        "objective": objective, # Store objective for debugging/context
                        "constraints": node_constraints, # <--- INJECT LOCAL CONSTRAINTS
                        "simulation_trace": beat_data.get("simulation_trace") # <-- THE MISSING PIECE
                    },
                    "context_snapshot": json.dumps(beat_data.get("resulting_state")) if beat_data.get("resulting_state") else "",
                }
                # Update in_memory_ledger with the successful resulting state
                if beat_data.get("resulting_state"):
                    in_memory_ledger = beat_data["resulting_state"]
                    logger.info(f"State carried forward to next beat. New Location: {in_memory_ledger.get('hard_state', {}).get('current_location_id')}")
            
            connection = {
                "from": current_node['node_id'],
                "to": child_id,
                "choice_label": child_node_data['content']['choice_label'],
                "joint_type": "DIRECT"
            }
            
            nodes.append(child_node_data)
            connections.append(connection)
            
            # PERSIST NODE & CONNECTION
            node_id_map = self._persist_nodes(volume_id, main_branch_id, [child_node_data], node_id_map)
            self._persist_connections(volume_id, [connection], node_id_map)
            
            # Step forward
            current_node = child_node_data

        # 3. Final Updates
        final_nodes = []
        for node in nodes:
            final_node = node.copy()
            final_node['node_id'] = node_id_map.get(node['node_id'])
            final_nodes.append(final_node)

        final_connections = []
        for conn in connections:
            final_conn = conn.copy()
            final_conn['from'] = node_id_map.get(conn['from'])
            final_conn['to'] = node_id_map.get(conn['to'])
            final_connections.append(final_conn)
            
        final_graph = {
            "nodes": final_nodes,
            "connections": final_connections,
            "root_node_id": node_id_map.get(root_node_data['node_id'])
        }
        self.db.table("StoryVolumes").update({"graph_structure": final_graph, "status": "drafting"}).eq("id", volume_id).execute()
        
        logger.info(f"Volume {volume_id} designed successfully with {len(nodes)} directed nodes.")
        return volume_id

    def _derive_constraints(self, seed_prose: str) -> Dict[str, str]:
        """
        Analyzes the Seed Prose to extract 'Hard Brake' constraints.
        This prevents the 'Mini-Movie' effect where the AI resolves the whole saga in one chapter.
        """
        if not seed_prose:
            return {
                "termination_condition": "The moment the immediate objective is achieved.",
                "knowledge_horizon": "Only strictly local knowledge. No cosmic awareness.",
                "timeframe": "Short (Hours)",
                "distance": "Local (Miles)"
            }

        prompt = f"""
        Analyze this story prompt (Seed Prose) and extract the physical boundaries.
        
        SEED PROSE: "{seed_prose}"
        
        We are writing ONE chapter based on this. We must NOT go further.
        
        Return JSON:
        {{
            "termination_condition": "The exact physical moment the scene must stop (e.g. 'When she reaches the gate').",
            "knowledge_horizon": "What the character definitively DOES NOT know yet (e.g. 'Does not know the rock is magic').",
            "timeframe": "Estimated duration (e.g. '4 hours')",
            "distance": "Estimated physical travel (e.g. '2 miles')"
        }}
        """
        try:
            resp = self.llm.chat_completion(prompt, json_schema=None)
            return self._parse_json(resp)
        except Exception as e:
            logger.warning(f"Constraint extraction failed: {e}. Using defaults.")
            return {
                "termination_condition": f"When this event concludes: '{seed_prose[:50]}...'",
                "knowledge_horizon": "Limited to local context.",
                "timeframe": "4-6 Hours",
                "distance": "Local"
            }

    def _generate_root(self, topic: str, lenses: List[str] = None, time_range: Dict = None, project_id: str = None, user_id: str = None, seed_prose: str = None, archetype: str = None, prohibitions: List[str] = None, character_stances: Dict = None, narrative_ledger: List[str] = None, depth: int = 12, previous_context: str = None, termination_condition: str = None, physics_manifest: Dict = None) -> Dict:
        """
        V12 Fix: Creates a factual root node based on the starting state, not a forward-looking summary.
        This prevents metadata leakage into subsequent nodes.
        """
        logger.info("Generating factual root node...")

        title = f"Chapter Start: {topic}"
        summary = "The story begins."

        starting_ledger_snapshot = {}
        if physics_manifest and "starting_ledger" in physics_manifest:
            starting_ledger = physics_manifest.get("starting_ledger", {})
            starting_ledger_snapshot = starting_ledger
            location = starting_ledger.get("location", "an unknown place")
            inventory = starting_ledger.get("inventory", [])
            
            # Normalize location name for readability
            loc_name = location.replace('_', ' ').replace('loc ', '').title()
            
            summary = f"The scene opens at {loc_name}."
            if inventory:
                # Normalize inventory names
                inv_names = [item.replace('_', ' ').replace('item ', '').title() for item in inventory]
                summary += f" The character is carrying {', '.join(inv_names)}."

        # Constraints are still needed for the Scribe later.
        node_constraints = self.constraints.copy()
        node_constraints["termination_condition"] = termination_condition or self.constraints.get("termination_condition", "The moment the objective is achieved.")

        # The root node itself has no novelty, it's a statement of fact.
        score = 0.0
        feedback = "Root node (factual starting point)."
        
        return {
            "node_id": "node_root",
            "title": title,
            "type": "root",
            "content": {
                "summary": summary, 
                "novelty_score": score, 
                "feedback": feedback,
                "constraints": node_constraints
            },
            "context_snapshot": json.dumps(starting_ledger_snapshot),
        }

    def _is_repetitive(self, text1: str, text2: str, threshold: float = 0.75) -> bool:
        """
        Checks if two text blocks are too similar using SequenceMatcher.
        Returns True if similarity > threshold.
        """
        if not text1 or not text2: return False
        similarity = difflib.SequenceMatcher(None, text1, text2).ratio()
        return similarity > threshold

    def expand_node_task(self, volume_id: str, node_id: str, branch_id: str) -> list[dict]:
        """Interactive Task: Generates 3 divergent 'Ghost Paths' from a specific node."""
        node = crud.get_node(self.db, node_id)
        if not node: return []

        try:
             story_so_far = self.context_engine.get_context_from_db(volume_id, node_id)
        except Exception:
             story_so_far = node.content.get('summary', '')

        prompt = f"""
        You are the Architect. Generate 3 divergent options for what happens next after:
        "{node.content.get('title', 'Untitled')}"
        
        The Story So Far:
        {story_so_far}

        Return JSON list: [{{ "type": "...", "title": "...", "summary": "..." }}]
        """

        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            return self._parse_json(response) or []
        except Exception:
            return []
