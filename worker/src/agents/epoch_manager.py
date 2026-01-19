import logging
import json
from typing import List, Dict, Any, Optional
from .base import BaseAgent
from db import crud, schemas

logger = logging.getLogger(__name__)

class EpochManagerAgent(BaseAgent):
    """
    The Timekeeper.
    Responsible for managing Epoch transitions, consolidating memory,
    and maintaining the continuity of the narrative soul.
    """

    def consolidate_epoch(self, universe_id: str, epoch_id: int = None):
        """
        Closes the chapter on an Epoch.
        1. Prose Style Vector: Analyzes the epoch's text to capture the 'Voice'.
        2. Linear Memory: Summarizes the Narrative Ledger into a cohesive history.
        3. Wipe Ghosts: Deletes transient thought atoms to clean the slate.
        """
        logger.info(f"⏳ Consolidating Epoch for Universe {universe_id}...")
        
        # 1. Resolve Epoch ID
        if not epoch_id:
            uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
            if not uni_res.data or not uni_res.data.get('active_epoch_id'):
                logger.error("No active epoch found for universe.")
                return
            epoch_id = uni_res.data['active_epoch_id']

        # 2. Fetch Epoch Data
        epoch_res = self.db.table("Epochs").select("*").eq("id", epoch_id).single().execute()
        if not epoch_res.data:
            logger.error(f"Epoch {epoch_id} not found.")
            return
        
        epoch_data = epoch_res.data
        ledger = epoch_data.get('narrative_ledger', [])
        
        # --- A. LINEAR MEMORY SUMMARIZATION ---
        logger.info("  -> Generating Linear Memory Summarization...")
        linear_summary = self._generate_linear_memory(ledger, epoch_data.get('name'))
        
        # --- B. PROSE STYLE VECTOR ---
        logger.info("  -> Extracting Prose Style Vector...")
        style_summary, style_embedding = self._extract_prose_style(universe_id, epoch_id, epoch_data.get('seed_prose'))
        
        # Update Epoch with Summaries and Vector
        update_data = {
            "summary": linear_summary,
            "style_summary": style_summary
        }
        if style_embedding:
            update_data["style_embedding"] = style_embedding

        self.db.table("Epochs").update(update_data).eq("id", epoch_id).execute()
        logger.info(f"Epoch {epoch_id} consolidated. Summary len: {len(linear_summary)}. Style: {style_summary[:50]}...")

        # --- C. WIPE GHOST NODES ---
        logger.info("  -> Wiping Ghost Nodes (Transient Thoughts)...")
        self._wipe_ghost_nodes(universe_id, epoch_id)
        
        return {
            "epoch_id": epoch_id,
            "linear_summary": linear_summary,
            "style_summary": style_summary,
            "ghosts_wiped": True
        }

    def inherit_ledger(self, source_epoch_id: int, target_epoch_id: int):
        """
        Copies the logical state (Inventory, Quests, Flags) from one epoch to the next.
        This ensures physical/logical continuity even as narrative styles change.
        V11.9 - Now performs a deep merge to prevent state loss.
        """
        logger.info(f"📜 Inheriting Ledger from Epoch {source_epoch_id} to {target_epoch_id}...")
        
        # 1. Fetch both ledgers
        source_res = self.db.table("Epochs").select("narrative_ledger").eq("id", source_epoch_id).single().execute()
        if not source_res.data:
            logger.warning(f"Source Epoch {source_epoch_id} ledger not found.")
            return
        
        source_ledger = source_res.data.get('narrative_ledger') or {}

        target_res = self.db.table("Epochs").select("narrative_ledger").eq("id", target_epoch_id).single().execute()
        target_ledger = {}
        if target_res.data:
            target_ledger = target_res.data.get('narrative_ledger') or {}

        # 1. Start with the new world state (Target)
        merged_ledger = target_ledger.copy()

        # 2. Extract the character's legacy (Source)
        source_hard = source_ledger.get("hard_state", {})
        target_hard = merged_ledger.get("hard_state", {})

        # 3. Merge the Pockets (Character Continuity)
        if source_hard and target_hard:
            # Merge Inventory: Current seed items + Previous saga items
            target_hard["inventory"] = list(set(target_hard.get("inventory", []) + source_hard.get("inventory", [])))
            # Merge Traits: Current seed traits + Previous transformations (Blue Essence)
            target_hard["traits"] = list(set(target_hard.get("traits", []) + source_hard.get("traits", [])))
            
            # IMPORTANT: We do NOT overwrite current_location_id. 
            # We let the new Epoch's Parser decide where the character is.

        # 4. Merge the Mood (Soft State Continuity)
        source_soft = source_ledger.get("soft_state", {})
        if source_soft:
            if "soft_state" not in merged_ledger: merged_ledger["soft_state"] = {}
            merged_ledger["soft_state"].update(source_soft)

        # 3. Perform update on target
        self.db.table("Epochs").update({"narrative_ledger": merged_ledger}).eq("id", target_epoch_id).execute()
        logger.info(f"Ledger Inherited and Merged successfully for Epoch {target_epoch_id}.")

    def _generate_linear_memory(self, ledger: Any, epoch_name: str) -> str:
        """Compresses the event ledger into a cohesive narrative history."""
        if not ledger:
            return f"The Epoch of {epoch_name} passed with no recorded events."
            
        # Ledger might be a list (chronological events) or dict (state vector)
        if isinstance(ledger, list):
            ledger_text = "\n".join([f"- {event}" for event in ledger])
        else:
            ledger_text = json.dumps(ledger, indent=2)
        
        prompt = f"""
        You are the Royal Historian.
        Summarize the following record of events and state changes (The Narrative Ledger) into a single, cohesive historical account.
        This summary will serve as the "Memory" for the next era.
        
        EPOCH: {epoch_name}
        
        LEDGER DATA:
        {ledger_text}
        
        Write a 1-2 paragraph summary in the past tense. Focus on the causal chain of events and major shifts in the world.
        """
        
        try:
            summary = self.llm.chat_completion(prompt, json_schema=None)
            return summary.strip()
        except Exception as e:
            logger.error(f"Failed to generate linear memory: {e}")
            return "History unclear."

    def _extract_prose_style(self, universe_id: str, epoch_id: int, seed_prose: str) -> tuple[str, List[float]]:
        """Analyzes Crystallized Thoughts to capture the stylistic DNA of the epoch."""
        atoms_res = self.db.table("Atoms")\
            .select("content")\
            .eq("universe_id", universe_id)\
            .eq("discovery_epoch_id", epoch_id)\
            .eq("type", "crystallized_thought")\
            .limit(10)\
            .execute()
            
        corpus = ""
        if atoms_res.data:
            corpus = "\n\n".join([a['content'][:2000] for a in atoms_res.data])
        else:
            corpus = seed_prose or "Standard narrative style."

        prompt = f"""
        Analyze the writing style of the following text.
        Describe the Tone, Pacing, Vocabulary, and Atmosphere in 2-3 sentences.
        Example: "Dark, gritty, and industrial. Short, punchy sentences with technical jargon."
        
        TEXT SAMPLE:
        {corpus[:4000]}
        """
        
        try:
            style_desc = self.llm.chat_completion(prompt, json_schema=None)
            style_desc = style_desc.strip()
            embedding = self.llm.get_embedding(style_desc)
            return style_desc, embedding
        except Exception as e:
            logger.error(f"Failed to extract prose style: {e}")
            return "Unknown style.", None

    def _wipe_ghost_nodes(self, universe_id: str, epoch_id: int):
        """Removes transient nodes to prevent context pollution."""
        try:
            types_to_wipe = ["thought", "story_node"]
            self.db.table("Atoms").delete()\
                .eq("universe_id", universe_id)\
                .eq("discovery_epoch_id", epoch_id)\
                .in_("type", types_to_wipe)\
                .execute()
            logger.info(f"👻 Ghost Protocol Active: Wiped transient nodes for Epoch {epoch_id}.")
        except Exception as e:
            logger.error(f"Failed to wipe ghost nodes: {e}")
