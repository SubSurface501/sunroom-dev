import logging
from typing import Dict
from llm.client import get_llm_client
from db import crud

logger = logging.getLogger(__name__)

class CollaborativePlanner:
    def __init__(self, db):
        self.db = db
        self.llm = get_llm_client()

    def generate_collaborative_transcript(self, prompt: str, collaborator_map: Dict[str, str], volume_id: str):
        """
        Coordinates a multi-user session.
        collaborator_map format: {'Role Name': 'user_id_uuid'}
        """
        logger.info(f"🤝 Starting Collaborative Session for: {prompt}")
        logger.info(f"   Participants: {list(collaborator_map.keys())}")
        
        # 1. Decomposition Plan
        # We ask the LLM to route specific sub-problems to the specific expert roles.
        planning_prompt = f"""
        You are the Orchestrator of a multi-disciplinary team.
        Goal: "{prompt}"
        
        Team Members:
        {', '.join(collaborator_map.keys())}
        
        Task: Break the goal into distinct sub-questions, assigning each to the most relevant Team Member.
        Format your response exactly as:
        RoleName: Question
        """
        plan_text = self.llm.chat_completion(planning_prompt)
        logger.info(f"📋 Collaboration Plan:\n{plan_text}")
        
        # 2. Lensed Retrieval (Gathering Wisdom)
        context_buffer = []
        
        lines = plan_text.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                role = parts[0].strip()
                sub_question = parts[1].strip()
                
                # Loose matching for role names in case LLM adds/removes punctuation
                matched_role_key = None
                for key in collaborator_map.keys():
                    if key.lower() in role.lower() or role.lower() in key.lower():
                        matched_role_key = key
                        break
                
                if matched_role_key:
                    user_id = collaborator_map[matched_role_key]
                    logger.info(f"🔍 Searching {matched_role_key}'s Graph (User {user_id[:8]}...) for: {sub_question}")
                    
                    # Embed the sub-question
                    embedding = self.llm.get_embedding(sub_question)
                    
                    # CALL THE LENSED SEARCH
                    atoms = crud.match_atoms_hybrid(
                        self.db, 
                        sub_question, 
                        embedding, 
                        0.5, 
                        3, 
                        target_user_id=user_id # <--- The Lens is applied here
                    )
                    
                    if atoms:
                        wisdom = "\n".join([f"- {a['content']}" for a in atoms])
                        context_buffer.append(f"### INPUT FROM {matched_role_key.upper()}:\n{wisdom}\n")
                    else:
                        context_buffer.append(f"### INPUT FROM {matched_role_key.upper()}:\n(No specific records found in their graph, relying on general expertise)\n")

        full_context = "\n".join(context_buffer)
        
        # 3. Braided Synthesis
        # Combine the distinct inputs into a novel solution
        synthesis_prompt = f"""
        Generate a cohesive transcript that solves the problem by synthesizing the provided perspectives. 
        
        Problem: {prompt}
        
        {full_context}
        
        Instructions:
        1. Do not just list the inputs.
        2. "Braid" them together: Show how the perspective of one expert reinforces or modifies the other.
        3. Create a solution that neither could have achieved alone.
        """
        
        transcript = self.llm.chat_completion(synthesis_prompt)
        return transcript
