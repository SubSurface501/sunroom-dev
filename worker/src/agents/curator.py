import logging
import json
from db import crud
from db.schemas import Atom
from llm.client import get_llm_client

logger = logging.getLogger(__name__)

class CuratorAgent:
    def __init__(self, db, worker=None):
        self.db = db
        self.worker = worker
        self.llm = get_llm_client()

    def analyze_and_generate_trailheads(self, user_id: str, core_themes: str, volume_id: str = None):
        logger.info(f"🧐 Curator scanning for user {user_id} against themes: {core_themes}")
        
        # 1. Fetch recent 'Fact' atoms (Raw material)
        # We look for atoms created recently. If volume_id is provided, filter by it.
        # Otherwise, just grab recent atoms.
        query = self.db.table("Atoms").select("content").eq("user_id", user_id)
        if volume_id:
            query = query.eq("volume_id", volume_id)
            
        # Limit to 50 most recent to ensure freshness
        response = query.order("created_at", desc=True).limit(50).execute()
        facts = [a['content'] for a in response.data if a.get('content')]
        
        if not facts:
            logger.info("Curator found no facts to analyze.")
            return "No new facts to analyze."

        # 2. The 'Void Space' Analysis
        prompt = f"""
        You are a Content Strategist for a deep-dive video channel.
        
        Core Themes: {core_themes}
        
        Recent Ingested Knowledge (Raw Material):
        {json.dumps(facts[:20])} 
        
        Task: Identify 3 "Unexplored Trailheads" (Video Ideas) that:
        1. Utilize this new knowledge.
        2. Align with the Core Themes.
        3. Have NOT been covered yet.
        
        For each, assign two "Agent Personas" (e.g., Historian, Engineer) that should collaborate on it.
        
        Return JSON format ONLY:
        [
            {{
                "title": "Video Title",
                "premise": "The core argument...",
                "agent_a": "Role",
                "agent_b": "Role"
            }}
        ]
        """
        
        try:
            # Generate and Parse
            response_text = self.llm.chat_completion(prompt)
            
            # Simple clean up for markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
                
            trailheads = json.loads(response_text)
            
            # 3. Save as 'Trailhead' Atoms (The Notification)
            count = 0
            for t in trailheads:
                # We use the generic Atom schema, but type='trailhead'
                # Content is the JSON string of the trailhead config
                atom_data = {
                    "content": json.dumps(t), 
                    "type": "trailhead",      
                    "name": t['title'],
                    "user_id": user_id,      
                    "embedding": self.llm.get_embedding(t['title']),
                    "metadata": {
                        "is_curated": True,
                        "agent_a": t['agent_a'],
                        "agent_b": t['agent_b'],
                        "premise": t['premise']
                    }
                }
                if volume_id:
                    atom_data["metadata"]["volume_id"] = volume_id

                self.db.table("Atoms").insert(atom_data).execute()
                count += 1
                
            logger.info(f"Curator successfully generated {count} trailheads.")
            return f"Generated {count} new Trailheads."
            
        except Exception as e:
            logger.error(f"Curator failed: {e}", exc_info=True)
            return "Analysis failed."
