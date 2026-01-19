import logging
import json
import time
from typing import List, Dict, Any
from .base import BaseAgent
from worker.src.simulation.engine import PhysicsEngine
from .cognitive.planner import CognitivePlanner
from .cognitive.memory import MemoryStream
# CRITICAL IMPORT: Needed to catch the "Fail-Closed" error
from .reviewer import CanonViolationError

logger = logging.getLogger(__name__)

class SimulationAgent(BaseAgent):
    """
    The Timekeeper & Orchestrator.
    Manages the lifecycle of a simulation: Casting -> Loop -> Transcript.
    Bridges the gap between Abstract Blueprint and Concrete Prose.
    """

    def run_simulation(self, scene_context: str, characters: List[Dict], user_id: str, universe_id: str, epoch_id: int, initial_ledger: Any, turns: int = 5, system_prompt_anchor: str = None, prohibitions: List[str] = None) -> str:
        """
        Runs a multi-agent simulation for a given scene.
        """
        logger.info(f"Starting Simulation with {len(characters)} agents for {turns} turns. Anchor: {system_prompt_anchor[:30] if system_prompt_anchor else 'None'} | Universe: {universe_id}")
        
        # --- PHASE 1: INITIALIZATION ---
        
        # 1. Load World Bible
        from worker.src.context_frame import WorldBible, NarrativeLedger # Assuming these are available
        from worker.src.agents.architect_v2 import VolumeArchitectAgent # For _load_bible_and_state
        
        # Temporarily use Architect's method to load bible and ledger
        temp_architect_agent = VolumeArchitectAgent(self.db, self.worker, self.llm)
        bible, _ = temp_architect_agent._load_bible_and_state(universe_id, epoch_id)
        
        physics_engine = PhysicsEngine(bible)
        current_ledger = initial_ledger.model_copy(deep=True) if initial_ledger else NarrativeLedger()

        # 2. Initialize Agents (The Minds)
        active_agents = {}
        
        for char in characters:
            agent_id = char.get('id', char.get('name'))
            name = char.get('name', 'Unknown')
            desc = char.get('description', '')
            goal = char.get('goal', 'Survive and advance the plot.')
            
            # A. Memory (Hippocampus)
            mem_stream = MemoryStream(user_id=user_id, db=self.db, llm=self.llm, universe_id=universe_id) # ISOLATION FIX
            
            # Inject Backstory
            mem_stream.add_observation(f"I am {name}. {desc}. My goal is: {goal}.")
            
            # B. Planner (Frontal Lobe)
            planner = CognitivePlanner(memory_stream=mem_stream, llm_client=self.llm)
            
            active_agents[agent_id] = {
                "planner": planner,
                "memory": mem_stream,
                "meta": char,
                "current_observation": f"You are in {scene_context}. You see {', '.join([c['name'] for c in characters if c['name'] != name])}."
            }
            
        # --- PHASE 2: THE LOOP ---
        
        transcript = []
        transcript.append(f"SCENE SETUP: {scene_context}\nCAST: {', '.join([c['name'] for c in characters])}\n")
        
        for turn in range(1, turns + 1):
            logger.info(f"--- Turn {turn}/{turns} ---")
            transcript.append(f"\n[TURN {turn}]")
            
            # A. Parallel Thinking (Gather Intentions)
            intended_actions = {}
            
            for agent_id, agent_data in active_agents.items():
                planner = agent_data['planner']
                obs = agent_data['current_observation']
                goal = agent_data['meta']['goal']
                persona = agent_data['meta']
                
                # The Deliberation
                plan = planner.deliberate(persona=persona, observation=obs, goal=goal, current_ledger=current_ledger.dict())
                
                # The LLM generates actions in dict format, need to convert to ActionType
                action_data = plan.get('action', {"action_type": "wait", "target_id": "self"})
                intended_actions[agent_id] = action_data
            
            # B. World Step (Execute Actions via PhysicsEngine)
            observations = {}
            for agent_id, action_data in intended_actions.items():
                try:
                    action_type = action_data.get('action_type')
                    # Map dict to Pydantic Action object (similar to Architect's _grow_linear_beat)
                    from worker.src.simulation.actions import MoveAction, TakeAction, InspectAction, SpeakAction, AttackAction, UseAction, DropAction
                    cls_map = {
                        "move": MoveAction, "take": TakeAction, "inspect": InspectAction,
                        "speak": SpeakAction, "attack": AttackAction, "use": UseAction, "drop": DropAction,
                        "wait": MoveAction # Default to move/wait if action is not specific
                    }
                    
                    if action_type not in cls_map: 
                        logger.warning(f"Unknown action type: {action_type}. Defaulting to wait.")
                        action_obj = MoveAction(action_type="wait", target_id="self")
                    else:
                        action_obj = cls_map[action_type](**action_data)

                    new_ledger, result = physics_engine.execute_action(current_ledger, action_obj)
                    current_ledger = new_ledger # Update the ledger for the next action/turn
                    observations[agent_id] = result.message
                    transcript.append(f"SIMULATION RESULT ({active_agents[agent_id]['meta']['name']}): {result.dict()}")
                    
                    # Check for Canon Violations from PhysicsEngine result
                    if not result.success and "CanonViolation" in result.message: # Or a specific result.type
                        raise CanonViolationError(result.message)

                except CanonViolationError as e:
                    logger.warning(f"⚠️ Simulation attempted Canon Violation: {e}. Reverting action.")
                    observations[agent_id] = f"You hesitate, feeling a strange resistance in the air. {e}"
                    transcript.append(f"[SYSTEM NOTICE]: Reality Stability Failure detected. {e}. The timeline corrects itself.")
                except Exception as e:
                    logger.error(f"Critical Simulation Error during action execution: {e}")
                    observations[agent_id] = f"An error prevented your action: {e}"
                    transcript.append("[SYSTEM ERROR]: Simulation desynchronized during action execution.")
            
            # C. Process Results & Encode Memory
            # Director state is now derived from current_ledger
            transcript.append(f"STATE: Current Location: {current_ledger.hard_state.current_location_id}, Inventory: {current_ledger.hard_state.inventory}")
            
            for agent_id, action_data in intended_actions.items():
                name = active_agents[agent_id]['meta']['name']
                result_obs = observations.get(agent_id, "Nothing significant happened.")
                
                # 1. Update Agent's Context
                active_agents[agent_id]['current_observation'] = result_obs
                
                # 2. Encode to Memory
                memory_text = f"Turn {turn}: I attempted to '{action_data.get('action_type', 'unknown')}' on '{action_data.get('target_id', 'unknown')}'. Result: {result_obs}"
                active_agents[agent_id]['memory'].add_observation(memory_text)
                
                # 3. Log to Transcript
                transcript.append(f"ACTION ({name}): {action_data}")
                transcript.append(f"RESULT ({name}): {result_obs}")
                
        # --- PHASE 3: THE WRAP ---
        
        final_transcript = "\n".join(transcript)
        logger.info("Simulation Complete.")
        return final_transcript
                
        # --- PHASE 3: THE WRAP ---
        
        final_transcript = "\n".join(transcript)
        logger.info("Simulation Complete.")
        return final_transcript