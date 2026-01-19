import json
import re
from celery import Celery
from supabase import Client
from llm.client import LLMClient

class BaseAgent:
    """
    Base class for all agents, providing common dependencies.
    """
    def __init__(self, db: Client, worker: Celery, llm: LLMClient):
        self.db = db
        self.worker = worker
        self.llm = llm

    def _parse_json(self, text: str):
        """
        Robustly parses JSON from LLM output, handling code blocks and potential noise.
        """
        if not text:
            return None
            
        try:
            # 1. Try direct parsing
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Extract from code blocks
        match = re.search(r"```json\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. Last ditch: try to find the first { and last }
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])
            
            start_list = text.find('[')
            end_list = text.rfind(']') + 1
            if start_list != -1 and end_list != -1:
                return json.loads(text[start_list:end_list])

        except json.JSONDecodeError:
            pass
            
        return None
