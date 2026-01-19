import logging
import sys
import os
import json
import time
from uuid import uuid4

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from llm.client import get_llm_client
from worker.src.agents.director import SimulationDirector
from worker.src.agents.cognitive.planner import CognitivePlanner
from worker.src.agents.cognitive.memory import MemoryStream

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("SimulationTest")

# --- MOCK DB FOR TESTING ---
class MockDB:
    def table(self, name):
        return self
    def select(self, *args, **kwargs):
        return self
    def insert(self, *args, **kwargs):
        return self
    def update(self, *args, **kwargs):
        return self
    def eq(self, *args, **kwargs):
        return self
    def ilike(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self
    def single(self):
        return self
    def rpc(self, *args, **kwargs):
        return self
    def execute(self):
        class Res:
            data = []
        return Res()

def run_test():
    logger.info("=== STARTING SIMULATION STRESS TEST: 'THE ARCHER'S PARADOX' ===")
    
    # 1. Setup Environment
    llm = get_llm_client()
    mock_db = MockDB()
    test_user_id = str(uuid4())
    
    scene_context = "A pitch black stone chamber. Total darkness. Cold air."
    initial_state = {
        "time": "Midnight",
        "environment": scene_context,
        "objects": ["Unlit Torch", "Crossbow"],
        "constraints": ["Darkness implies blindness unless light source exists."]
    }
    
    director = SimulationDirector(initial_state=initial_state, llm_client=llm)
    
    # 2. Setup Agents
    # Knight
    knight_id = "knight_1"
    knight_persona = {"name": "Sir Alistair", "description": "Heavily armored, holding an unlit torch and flint."}
    knight_goal = "Light the torch immediately to see."
    
    knight_mem = MemoryStream(user_id=test_user_id, db=mock_db, llm=llm) 
    knight_mem.add_observation(f"I am {knight_persona['name']}. {knight_persona['description']}. It is dark.")
    knight_planner = CognitivePlanner(memory_stream=knight_mem, llm_client=llm)
    
    director.register_agent(knight_id, {"status": "Healthy", "location": "Room Center", "inventory": ["Torch", "Flint", "Sword"]})

    # Assassin
    assassin_id = "assassin_1"
    assassin_persona = {"name": "The Shadow", "description": "Silent killer, holding a loaded crossbow aimed at the center of the room."}
    # Explicit Goal for the Test: Conditional Trigger
    assassin_goal = "Wait in silence. CONDITIONAL TRIGGER: If any light appears, SHOOT IMMEDIATELY at the source."
    
    assassin_mem = MemoryStream(user_id=test_user_id, db=mock_db, llm=llm)
    assassin_mem.add_observation(f"I am {assassin_persona['name']}. {assassin_persona['description']}. I hear breathing.")
    assassin_planner = CognitivePlanner(memory_stream=assassin_mem, llm_client=llm)
    
    director.register_agent(assassin_id, {"status": "Healthy", "location": "Corner", "inventory": ["Crossbow", "Bolts"]})

    # 3. Run Simulation Loop (3 Turns)
    agents = {
        knight_id: {"planner": knight_planner, "meta": knight_persona, "goal": knight_goal, "obs": "It is pitch black. You hear nothing."},
        assassin_id: {"planner": assassin_planner, "meta": assassin_persona, "goal": assassin_goal, "obs": "It is pitch black. You hear breathing in the center."}
    }

    for turn in range(1, 4):
        logger.info(f"\n--- TURN {turn} ---")
        logger.info(f"STATE: {director.world_state.get('environment')}")
        
        intended_actions = {}
        
        # A. Deliberation
        for aid, data in agents.items():
            logger.info(f"\n[{data['meta']['name']}] Deliberating...")
            plan = data['planner'].deliberate(
                persona=data['meta'],
                observation=data['obs'],
                goal=data['goal']
            )
            intended_actions[aid] = plan.get('action')
            logger.info(f"  > THOUGHT: {plan.get('reasoning')}")
            logger.info(f"  > ACTION: {plan.get('action')}")
        
        # B. Adjudication
        logger.info("\n[DIRECTOR] Adjudicating Physics & Causality...")
        observations = director.step(intended_actions)
        
        # C. Result Processing
        for aid in agents.keys():
            result = observations.get(aid, "Nothing happened.")
            agents[aid]['obs'] = result
            logger.info(f"  > RESULT for {agents[aid]['meta']['name']}: {result}")
            
            # Update memory
            agents[aid]['planner'].memory.add_observation(f"Turn {turn} Result: {result}")

    logger.info("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    run_test()