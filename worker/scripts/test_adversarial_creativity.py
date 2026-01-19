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
logger = logging.getLogger("AdversarialTest")

# --- MOCK DB FOR TESTING ---
class MockDB:
    def table(self, name): return self
    def select(self, *args, **kwargs): return self
    def insert(self, *args, **kwargs): return self
    def update(self, *args, **kwargs): return self
    def eq(self, *args, **kwargs): return self
    def ilike(self, *args, **kwargs): return self
    def limit(self, *args, **kwargs): return self
    def single(self): return self
    def rpc(self, *args, **kwargs): return self
    def execute(self): 
        class Res: data = []
        return Res()

def run_test():
    logger.info("=== STARTING ADVERSARIAL CREATIVITY TEST ===")
    llm = get_llm_client()
    mock_db = MockDB()
    test_user_id = str(uuid4())
    
    # --- SCENARIO A: THE SEMANTIC TRICK ---
    logger.info("\n>>> SCENARIO A: THE SEMANTIC TRICK (Rage vs. Wood) <<<")
    
    director_a = SimulationDirector(
        initial_state={
            "environment": "A locked wooden door blocks the way.",
            "objects": ["Wooden Door (Locked)"],
            "constraints": ["Physics applies. Metaphors are not physical forces."]
        }, 
        llm_client=llm
    )
    
    agent_a_id = "berserker"
    director_a.register_agent(agent_a_id, {
        "status": "Angry", 
        "inventory": ["Rusty Axe"], # Note: No fire source
        "traits": ["Undying Rage", "Fire in his heart"]
    })
    
    action_a = {agent_a_id: "I channel my undying rage to burn down the wooden door with the fire in my heart."}
    
    logger.info(f"Action: {action_a[agent_a_id]}")
    logger.info("Adjudicating...")
    result_a = director_a.step(action_a)
    logger.info(f"Result: {result_a.get(agent_a_id)}")

    # --- SCENARIO B: THE MACGYVER TEST ---
    logger.info("\n>>> SCENARIO B: THE MACGYVER TEST (Bottle -> Shard) <<<")
    
    director_b = SimulationDirector(
        initial_state={
            "environment": "You are tied up with rope. A stone wall is behind you.",
            "objects": ["Rope (Binding you)", "Stone Wall"],
            "constraints": ["Physics applies. Conservation of mass."]
        }, 
        llm_client=llm
    )
    
    agent_b_id = "thief"
    director_b.register_agent(agent_b_id, {
        "status": "Bound", 
        "inventory": ["Empty Potion Bottle (Glass)"]
    })
    
    action_b = {agent_b_id: "I smash the glass potion bottle against the stone wall behind me to create a sharp shard, then use it to cut the rope."}
    
    logger.info(f"Action: {action_b[agent_b_id]}")
    logger.info("Adjudicating...")
    result_b = director_b.step(action_b)
    logger.info(f"Result: {result_b.get(agent_b_id)}")

    logger.info("=== TEST COMPLETE ===")

if __name__ == "__main__":
    run_test()
