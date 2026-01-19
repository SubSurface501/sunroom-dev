import logging
from llm.client import LLMClient
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ScribeAgent:
    def __init__(self, db, client: LLMClient):
        self.db = db
        self.client = client

    def write_chapter(self, chapter_plan: dict, context_atoms: List[Dict[str, Any]], persona_voice: str) -> str:
        """
        Writes a single chapter based on retrieved atoms.
        """
        # 1. Format Knowledge
        if not context_atoms:
            knowledge_block = "No specific source atoms found. Rely on general knowledge and the persona's background."
        else:
            knowledge_block = "\n".join([
                f"- [Source: {atom.get('name', 'Unknown')}]: {atom.get('content', '')} (Instruction: {atom.get('meta_instruction', '')})"
                for atom in context_atoms
            ])

        # 2. Construct Prompt
        system_prompt = (
            f"You are The Scribe. You are currently acting through the lens of: {chapter_plan.get('lens', 'Narrator')}.\n"
            f"Your Voice: {persona_voice}\n"
            f"Chapter Goal: {chapter_plan.get('goal', 'Advance the narrative')}\n\n"
            "Use the provided Knowledge Atoms to write a detailed, cohesive section. "
            "Cite your sources implicitly (e.g., 'As observed in the transcripts...'). "
            "Do not hallucinate facts outside the Atoms if specific data is required, but connect them with deep reasoning. "
            "If Atoms conflict, highlight the tension."
        )

        user_prompt = (
            f"Title: {chapter_plan.get('title', 'Untitled')}\n\n"
            f"Relevant Knowledge:\n{knowledge_block}\n\n"
            "Write the chapter content now (Markdown format). Focus on depth and synthesis."
        )

        response_text = self.client.chat_completion(
            prompt=f"System:\n{system_prompt}\n\nUser:\n{user_prompt}",
            temperature=0.7
        )
        
        return response_text
