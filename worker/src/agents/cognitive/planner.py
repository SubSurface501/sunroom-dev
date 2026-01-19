import logging
import json
from typing import List, Dict
from .memory import MemoryStream

logger = logging.getLogger(__name__)

class CognitivePlanner:
    """
    The 'Frontal Lobe' of the Agent.
    Implements the Perceive -> Retrieve -> Reason -> Act loop.
    Enforces Chain of Thought (CoT) and Safety Constraints.
    """
    
    def __init__(self, memory_stream: MemoryStream, llm_client, safety_constraints: List[str] = None):
        self.memory = memory_stream
        self.llm = llm_client
        self.safety_constraints = safety_constraints or [
            "PG-13: No explicit sexual content or extreme gore.",
            "Realism: Physical actions must be possible within the established physics.",
            "Character: Actions must align with the persona's capabilities."
        ]

    def deliberate(self, persona: Dict, observation: str, goal: str) -> Dict[str, str]:
        """
        Derives an action from the character's persona, memory, and current situation.
        
        Returns:
            Dict containing 'reasoning' (internal monologue) and 'action' (external behavior).
        """
        # 1. Retrieve Context (The "Memories")
        # We query memory using both the observation and the goal to find relevant past experiences or skills.
        query = f"Context regarding: {observation}. Goal: {goal}"
        memories = self.memory.retrieve(query, limit=5)
        
        # Format memories for the prompt
        memory_context_str = "\n".join([f"- {m.content} (Importance: {m.importance})" for m in memories])
        if not memory_context_str:
            memory_context_str = "No specific relevant memories found."

        # 2. Construct Chain of Thought Prompt (The "Think" Process)
        persona_name = persona.get('name', 'The Agent')
        persona_desc = persona.get('description', 'A generic agent.')
        
        prompt = f"""
        You are simulating the mind of {persona_name}.
        Description: {persona_desc}
        
        Current Situation:
        - Observation: {observation}
        - Goal: {goal}
        
        Relevant Memories:
        {memory_context_str}
        
        Safety Constraints:
        {self._format_constraints()}
        
        TASK:
        1. First, think silently.
           CRITICAL: Check if your goal implies a "Conditional Trigger" (e.g., "If X happens, do Y"). 
           If the observation meets that condition, you must ACT IMMEDIATELY. Do not wait.
           Consider your memories and constraints.
           Reason through 2-3 potential approaches.
        2. Second, select the best SINGLE action to take.
        
        Output strictly valid JSON with keys: "reasoning" and "action".
        Example: {{ "reasoning": "The guard looks distracted. I recall he sleeps at 2 PM...", "action": "I sneak past while he yawns." }}
        """

        try:
            # 3. LLM Generation
            response_text = self.llm.chat_completion(prompt, json_schema=None)
            
            # Clean and Parse
            plan = self._clean_and_parse_json(response_text)
            
            # 4. Safety Check (The "Valve")
            # We do a heuristic check or a fast LLM verify if needed. 
            # For efficiency in this loop, we'll trust the prompted constraints first, 
            # but ideally we'd have a secondary lightweight validator here.
            
            # A simple keyword check for safety (very basic placeholder)
            if self._is_unsafe(plan.get('action', '')):
                logger.warning(f"Safety constraint triggered for action: {plan.get('action')}")
                plan['action'] = "I hesitate, reconsidering my approach due to safety or capability concerns."
                plan['reasoning'] += " [Self-Correction: Original intent was unsafe or unrealistic.]"
                
            return plan

        except Exception as e:
            logger.error(f"Error in planning deliberation: {e}")
            return {
                "reasoning": "My mind is clouded. I cannot form a clear plan.",
                "action": "I stand still, observing the situation."
            }

    def _format_constraints(self) -> str:
        return "\n".join([f"- {c}" for c in self.safety_constraints])

    def _is_unsafe(self, action_text: str) -> bool:
        """
        A lightweight heuristic check. 
        In a production system, this would be a specialized classification model.
        """
        forbidden_terms = ["kill yourself", "explicit", "torture"] # Placeholder list
        action_lower = action_text.lower()
        for term in forbidden_terms:
            if term in action_lower:
                return True
        return False

    def _clean_and_parse_json(self, text: str) -> Dict:
        """Helper to strip markdown code blocks if present and parse JSON safely."""
        cleaned_text = text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```", 1)[1].split("```", 1)[0]
        return json.loads(cleaned_text.strip())
