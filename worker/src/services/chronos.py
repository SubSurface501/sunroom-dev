import re
import json
import logging
from datetime import datetime
from typing import Tuple
from llm.client import get_llm_client

logger = logging.getLogger(__name__)

class ChronosService:
    def __init__(self):
        self.llm = get_llm_client()

    def determine_date(self, text_snippet: str, filename: str = "", source_type: str = "uploaded_text") -> Tuple[datetime | None, float]:
        """
        Returns (datetime, confidence_score)
        strategies: Deterministic > Heuristic > LLM
        """
        
        # Strategy 1: Heuristic (Regex on Filename/Header)
        # Look for YYYY-MM-DD or YYYY_MM_DD or just YYYY in filename if it looks like a year
        date_pattern = r"(\d{4})[-_](\d{2})[-_](\d{2})"
        
        # Check filename
        match = re.search(date_pattern, filename)
        if match:
            try:
                dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return dt, 0.9 # High confidence
            except ValueError:
                pass

        # Check first 500 chars of text (Header) for "Date: ..."
        # Simple pattern: Date: YYYY-MM-DD
        header_pattern = r"(?:Date|Written|Created):\s*(\d{4}-\d{2}-\d{2})"
        match = re.search(header_pattern, text_snippet[:500], re.IGNORECASE)
        if match:
             try:
                dt = datetime.fromisoformat(match.group(1))
                return dt, 0.9
             except ValueError:
                 pass

        # Strategy 2: The LLM "Historian" (Fallback)
        # Only for uploaded texts where we really don't know
        if source_type == "uploaded_text":
             return self._ask_llm_for_date(text_snippet[:1500])

        return None, 0.0

    def _ask_llm_for_date(self, text: str) -> Tuple[datetime | None, float]:
        prompt = f"""
        Analyze the following text fragment. Your goal is to determine the 
        ORIGINAL CREATION or PUBLICATION date.
        
        - If it's a diary entry, look for context clues ("Today is Christmas 2012").
        - If it's a classic text, estimate the historical year (e.g. Plato -> -380, represent as 0001-01-01 BC or just ignore BC for now and use year 1).
        - If it's modern technical documentation, look for version dates.
        
        Return ONLY a JSON object: {{ "date": "YYYY-MM-DD", "confidence": float }}
        If unknown, return {{ "date": null, "confidence": 0.0 }}
        
        TEXT:
        {text}
        """
        try:
            response = self.llm.chat_completion(prompt, json_schema={"type": "object", "properties": {"date": {"type": "string"}, "confidence": {"type": "number"}}})
            # Clean response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            data = json.loads(response.strip())
            date_str = data.get("date")
            confidence = data.get("confidence", 0.0)
            
            if date_str:
                try:
                    # Handle just YYYY
                    if len(date_str) == 4:
                        dt = datetime(int(date_str), 1, 1)
                    else:
                        dt = datetime.fromisoformat(date_str)
                    return dt, confidence
                except ValueError:
                    logger.warning(f"Chronos failed to parse LLM date: {date_str}")
                    
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Chronos LLM check failed: {e}")
            return None, 0.0
