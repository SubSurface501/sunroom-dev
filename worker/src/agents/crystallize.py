import logging
import json
import uuid
from typing import List, Dict, Any
from .base import BaseAgent
from db import crud, schemas
import datetime

logger = logging.getLogger(__name__)

class CrystallizeVolumeAgent(BaseAgent):
    """
    The Crystallizer.
    Responsible for taking a finished Story Volume and 'hardening' it into the permanent record.
    1. Creates a 'crystallized_thought' Atom containing the full text.
    2. Updates the Collective Graph (AtomEdges) with the approved narrative paths.
    3. (Narrative Evolution) Updates the Epoch Ledger and Character Stances.
    """
    def __init__(self, db, worker, llm):
        super().__init__(db, worker, llm)
        from .domain_expert import DomainExpertAgent
        self.domain_expert = DomainExpertAgent(db, worker, llm)

    def run_task(self, volume_id: str):
        logger.info(f"Crystallizing Volume {volume_id}...")
        
        # 1. Fetch Volume
        vol_res = self.db.table("StoryVolumes").select("*").eq("id", volume_id).execute()
        if not vol_res.data:
            logger.error(f"Volume {volume_id} not found.")
            return None
        
        volume = vol_res.data[0]
        
        # 2. Compile Content (The Full Manuscript)
        full_text = self._compile_volume_text(volume)
        
        # Fetch Universe Context if applicable
        universe_id = volume.get('universe_id')
        discovery_epoch_id = None
        if universe_id:
            try:
                uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
                if uni_res.data:
                    discovery_epoch_id = uni_res.data.get('active_epoch_id')
            except Exception as e:
                logger.warning(f"Failed to fetch active epoch for crystallization: {e}")
        
        # 3. Create Crystallized Atom (The Artifact)
        atom_data = {
            "user_id": volume['user_id'],
            "name": volume['title'],
            "type": "crystallized_thought",
            "content": full_text,
            "universe_id": universe_id, # Link to Universe
            "discovery_epoch_id": discovery_epoch_id, # Link to Epoch (Shadow Canon)
            "metadata": {
                "source": "StoryVolume", 
                "volume_id": volume_id,
                "project_id": volume.get('project_id')
            }
        }
        
        # Check if already exists to avoid dupes on re-runs
        existing = self.db.table("Atoms").select("id").eq("metadata->>volume_id", volume_id).execute()
        if existing.data:
            atom_id = existing.data[0]['id']
            self.db.table("Atoms").update(atom_data).eq("id", atom_id).execute()
            logger.info(f"Updated existing Crystallized Atom {atom_id}")
        else:
            res = self.db.table("Atoms").insert(atom_data).execute()
            atom_id = res.data[0]['id']
            logger.info(f"Created Crystallized Atom {atom_id}")
            
        # 4. Update Collective Graph (The "Crystallization" Protocol)
        graph = volume.get('graph_structure', {})
        if graph and 'connections' in graph and 'nodes' in graph:
            self._solidify_narrative_edges(volume['user_id'], volume.get('project_id'), graph, universe_id)

        # 5. Narrative Evolution (The Soul Update)
        if universe_id and full_text:
            self._update_character_evolution(volume, full_text)

        return atom_id

    def _update_character_evolution(self, volume: Dict, full_text: str):
        """
        The Narrative Evolution Engine.
        1. Summarizes the volume into major narrative events (The Ledger).
        2. Updates the Epoch's character stances based on the new ledger history.
        """
        logger.info("Engaging Narrative Evolution Engine...")
        
        uni_id = volume.get('universe_id')
        if not uni_id: return

        try:
            # 1. Fetch Universe to get Active Epoch
            uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", uni_id).single().execute()
            active_epoch_id = uni_res.data.get('active_epoch_id') if uni_res.data else None
            if not active_epoch_id: 
                logger.warning("No active epoch found for evolution.")
                return

            # 2. Fetch Active Epoch Data
            epoch_res = self.db.table("Epochs").select("*").eq("id", active_epoch_id).single().execute()
            epoch_data = epoch_res.data
            
            existing_ledger = epoch_data.get('narrative_ledger', [])
            if not isinstance(existing_ledger, list): existing_ledger = []
            
            existing_stances = epoch_data.get('character_stances', {})
            if not isinstance(existing_stances, dict): existing_stances = {}

            # 3. Step A: Extract Volume Events (The Ledger Update)
            event_prompt = f"""
            Analyze the story volume: "{volume['title']}".
            Identify 1-3 major turning points or significant events that happened.
            Format each as a single concise sentence (e.g., "Kaelen discovered the crystalline ruins of Aethelgard.").
            
            STORY SUMMARY:
            {full_text[:3000]}
            
            Return strictly valid JSON: {{ "events": ["...", "..."] }}
            """
            
            event_resp = self.llm.chat_completion(event_prompt, json_schema=None)
            if "```json" in event_resp: event_resp = event_resp.split("```json")[1].split("```")[0]
            elif "```" in event_resp: event_resp = event_resp.split("```")[1].split("```")[0]
            
            new_events = json.loads(event_resp.strip()).get('events', [])
            updated_ledger = existing_ledger + new_events
            
            # 4. Step B: Update Stances (The Soul Evolution)
            evolution_prompt = f"""
            You are a Psychological Profiler for fictional characters.
            Analyze how the Protagonist's belief system has evolved based on the cumulative history of this Epoch.
            
            PREVIOUS STANCES:
            {json.dumps(existing_stances, indent=2)}
            
            CUMULATIVE NARRATIVE LEDGER (The History of this Epoch):
            {json.dumps(updated_ledger, indent=2)}
            
            TASK:
            1. Identify the Protagonist's name.
            2. Describe their *new* Epistemic Stance given these recent events.
            3. Focus on their belief in Magic vs Science / Rationality vs Wonder.
            
            Return strictly valid JSON: {{ "name": "...", "stance": "..." }}
            """
            
            stance_resp = self.llm.chat_completion(evolution_prompt, json_schema=None)
            if "```json" in stance_resp: stance_resp = stance_resp.split("```json")[1].split("```")[0]
            elif "```" in stance_resp: stance_resp = stance_resp.split("```")[1].split("```")[0]
            
            stance_data = json.loads(stance_resp.strip())
            
            char_name = stance_data.get('name', 'Protagonist')
            new_stance = stance_data.get('stance', '')
            
            updated_stances = existing_stances.copy()
            updated_stances[char_name] = new_stance

            # 5. Commit to DB
            self.db.table("Epochs").update({
                "narrative_ledger": updated_ledger,
                "character_stances": updated_stances
            }).eq("id", active_epoch_id).execute()
            
            logger.info(f"Narrative Evolution Complete. Ledger size: {len(updated_ledger)}. Updated stance for {char_name}.")

            # 6. Also save an Atom for traceability
            # Fix: Append UUID to name to prevent duplicate key errors
            unique_suffix = str(uuid.uuid4())[:8]
            atom_data = {
                "user_id": volume['user_id'],
                "name": f"Character Evolution: {char_name} ({unique_suffix})",
                "type": "character_stance",
                "content": new_stance,
                "universe_id": uni_id,
                "discovery_epoch_id": active_epoch_id,
                "metadata": {
                    "character_name": char_name,
                    "source_volume_id": volume['id'],
                    "ledger_snapshot": new_events
                }
            }
            self.db.table("Atoms").insert(atom_data).execute()
            
            # 7. Forward Propagation (The Infinite Staircase)
            self._propagate_evolution(uni_id, active_epoch_id, updated_stances)

        except Exception as e:
            logger.error(f"Failed narrative evolution: {e}", exc_info=True)

    def _propagate_evolution(self, universe_id: str, current_epoch_id: int, updated_stances: Dict):
        """
        Pushes the evolved character stances to the *next* chronological Epoch.
        MERGE STRATEGY: {**updated_stances, **existing_next_stances}
        This ensures History provides the baseline, but the Author's Future Plan (existing_next)
        takes precedence if they manually defined specific states (e.g., "Old Man").
        """
        try:
            # Find the immediate next epoch
            next_epoch_res = self.db.table("Epochs").select("id, character_stances")\
                .eq("universe_id", universe_id)\
                .gt("id", current_epoch_id)\
                .order("id")\
                .limit(1)\
                .execute()
                
            if not next_epoch_res.data:
                logger.info("No future epoch found for propagation. Evolution stops here.")
                return

            next_epoch = next_epoch_res.data[0]
            next_epoch_id = next_epoch['id']
            existing_next_stances = next_epoch.get('character_stances') or {}
            
            # Merge logic: History Base + Future Overlay
            merged_stances = {**updated_stances, **existing_next_stances}
            
            self.db.table("Epochs").update({"character_stances": merged_stances}).eq("id", next_epoch_id).execute()
            logger.info(f"Forward Propagation: Pushed evolved stances from Epoch {current_epoch_id} to Epoch {next_epoch_id}.")
            
        except Exception as e:
            logger.error(f"Failed to propagate evolution: {e}")

    def _compile_volume_text(self, volume: Dict) -> str:
        """Helper to stitch node summaries into a readable text."""
        graph = volume.get('graph_structure', {})
        text = [f"Title: {volume['title']}"]
        text.append(f"Summary: {volume.get('root_concept', '')}")
        
        # Simple compilation
        if graph.get('nodes'):
            for node in graph['nodes']:
                text.append(f"\n[{node['title']}]\n{node.get('summary', '')}")
                
        return "\n".join(text)

    def _solidify_narrative_edges(self, user_id: str, project_id: str, graph: Dict, universe_id: str = None):
        """
        Parses the volume graph and updates the AtomEdges table.
        This is the moment 'Creative Intent' becomes 'Ontological Fact'.
        """
        logger.info("Solidifying narrative edges into Knowledge Graph...")
        
        node_map = {n['node_id']: n for n in graph.get('nodes', [])}
        
        for conn in graph.get('connections', []):
            source_node = node_map.get(conn['from'])
            target_node = node_map.get(conn['to'])
            
            if not source_node or not target_node:
                continue
                
            # We need to map these *Volume Nodes* to *Concept Atoms*.
            # Strategy: Search for an existing Atom by title. If not found, create a 'concept' Atom.
            # This ensures the Graph grows with new concepts introduced in the story.
            
            source_atom_id = self._resolve_concept_atom(user_id, project_id, source_node['title'], universe_id)
            target_atom_id = self._resolve_concept_atom(user_id, project_id, target_node['title'], universe_id)
            
            if source_atom_id and target_atom_id and source_atom_id != target_atom_id:
                # Check for existing edge to prevent 409
                existing_edge = self.db.table("AtomEdges").select("id").eq("source_atom_id", source_atom_id).eq("target_atom_id", target_atom_id).execute()
                
                if not existing_edge.data:
                    # Insert the Edge
                    edge_data = {
                        "user_id": user_id,
                        "project_id": project_id,
                        "source_atom_id": source_atom_id,
                        "target_atom_id": target_atom_id,
                        "relationship_type": "narrative_flow",
                        "weight": 1.0, 
                        "metadata": {"volume_id": graph.get('root_node_id')} 
                    }
                    try:
                        self.db.table("AtomEdges").insert(edge_data).execute()
                    except Exception as e:
                        # Race condition fallback
                        pass

    def _resolve_concept_atom(self, user_id: str, project_id: str, title: str, universe_id: str = None) -> str:
        """Finds or creates a Concept Atom for the given title."""
        # 1. Search (Scoped to Universe if provided)
        query = self.db.table("Atoms").select("id").eq("user_id", user_id).ilike("name", title)
        if universe_id:
            query = query.eq("universe_id", universe_id)
        
        res = query.execute()
        if res.data:
            return res.data[0]['id']
            
        # 2. Create if missing
        new_atom = {
            "user_id": user_id,
            "name": title,
            "type": "concept", # It's a concept now
            "content": f"Concept extracted from story node '{title}'",
            "metadata": {"auto_generated": True},
            "universe_id": universe_id # <--- LEAK FIXED
        }
        if project_id:
            new_atom['metadata']['project_id'] = project_id

        try:
            res = self.db.table("Atoms").insert(new_atom).execute()
            return res.data[0]['id']
        except Exception as e:
            logger.error(f"Failed to create concept atom {title}: {e}")
            return None
