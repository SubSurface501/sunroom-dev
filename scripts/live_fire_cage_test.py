import os
import sys
import json
import logging
from typing import Dict, Any

# FORCE LOCAL REDIS
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.client import LLMClient
from worker.src.agents.reviewer import ReviewAgent, ReviewStatus, ViolationType

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LiveFireTest")

def run_live_fire_test():
    print("\n🔥 INITIATING LIVE FIRE CAGE TEST 🔥")
    print("---------------------------------------")
    
    # 1. Setup Real Agents (No Mocks)
    try:
        # We don't need a real DB connection if we pass explicit contexts
        mock_db = None 
        mock_worker = None
        
        # Real LLM Client (FORCE LIVE MODE)
        llm = LLMClient(debug_mode=False)
        print(f"✅ LLM Client Connected: {llm.text_model_name}")
        
        agent = ReviewAgent(mock_db, mock_worker, llm)
        print("✅ ReviewAgent Initialized")

    except Exception as e:
        print(f"❌ Setup Failed: {e}")
        return

    # 2. Define The Scenario
    # Scenario: A hard sci-fi universe where magic is banned.
    universe_rules = (
        "UNIVERSE: THE IRON COG.\n"
        "GENRE: Industrial Hard Sci-Fi.\n"
        "PHYSICS: Newtonian. No magic. No supernatural elements.\n"
        "TECHNOLOGY: Steam and early electricity only."
    )
    
    # BLIND TEST: No keywords. The AI must figure it out.
    prohibitions = [] 
    
    # The Violation Draft
    violation_draft = (
        "The wizard raised his staff and chanted the ancient words. "
        "A massive fireball erupted from the tip, consuming the steam engine in green flames. "
        "'That will teach you to trust in machines,' he laughed."
    )
    
    narrative_intent = "Show the protagonist fixing the steam engine using tools."

    print(f"\nSCENARIO (SEMANTIC BLIND TEST):\n   Universe: Industrial Hard Sci-Fi\n   Draft: '{violation_draft[:50]}...'\n   Intent: Fix engine with tools.\n")

    # 3. Execute The Review
    print("🚀 Sending to Gemini for Audit...")
    try:
        # We call the 'cage' directly via the agent's facade or internal method.
        # Since we modified ReviewAgent.run_task to use the Cage, we can use that.
        # However, run_task tries to flag the node in the DB.
        # Let's use agent.cage.review_draft directly to avoid DB dependency.
        from worker.src.agents.reviewer import OntologicalCage
        cage = OntologicalCage(agent)
        
        result = cage.review_draft(
            volume_id="TEST_VOL",
            node_id="TEST_NODE",
            draft_text=violation_draft,
            user_context="User Style: Analytical, Detailed.",
            domain_context=universe_rules,
            prohibitions=prohibitions,
            narrative_intent=narrative_intent
        )

        # 4. Analyze Results
        print("\n📊 RESULTS RECEIVED")
        print("-------------------")
        print(f"Status: {result.status.value.upper()}")
        print(f"Score:  {result.score}")
        print(f"Issues: {result.issues}")
        
        # 5. Save Report
        report_path = os.path.join("logs", "live_fire_report.json")
        os.makedirs("logs", exist_ok=True)
        
        output_data = {
            "scenario": {
                "universe": universe_rules,
                "draft": violation_draft,
                "intent": narrative_intent
            },
            "result": result.model_dump()
        }
        
        with open(report_path, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"\n💾 Full Report saved to: {report_path}")
        
        # Verification Logic
        if result.status in [ReviewStatus.HARD_FAIL, ReviewStatus.SOFT_FAIL] and result.score < 0.3:
            print("\n✅ TEST PASSED: The Cage successfully blocked the hallucination.")
        else:
            print("\n❌ TEST FAILED: The Cage allowed the violation!")

    except Exception as e:
        print(f"\n❌ Execution Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_live_fire_test()
