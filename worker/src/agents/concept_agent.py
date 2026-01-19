import logging
import json
from .base import BaseAgent
from prompts import CONCEPT_EXPANDER_PROMPT

logger = logging.getLogger(__name__)

class ConceptAgent(BaseAgent):
    """
    The Creative Producer.
    Expands a simple user prompt into a detailed, structured creative brief.
    """
    def run_task(self, user_prompt: str):
        logger.info(f"Expanding user prompt into a creative brief: '{user_prompt}'")

        prompt = CONCEPT_EXPANDER_PROMPT.format(user_prompt=user_prompt)

        try:
            response = self.llm.chat_completion(prompt, json_schema=None)
            
            # Clean up potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            
            concept_brief = json.loads(response.strip())
            
            logger.info("Successfully generated creative brief.")
            return concept_brief

        except Exception as e:
            logger.error(f"ConceptAgent failed to generate or parse creative brief: {e}")
            # In case of failure, we can return an error structure
            return {
                "error": True,
                "message": f"Failed to expand concept: {e}",
                "original_prompt": user_prompt
            }
