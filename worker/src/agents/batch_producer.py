import logging
import time
import json
from typing import Optional, List
from datetime import datetime, timezone
from .base import BaseAgent
# Import tasks to chain them directly or call agents directly?
# Since BatchProducer is an agent running inside Celery, it can dispatch sub-tasks or run logic.
# To avoid circular imports with tasks.py, we will use the Celery app signature if needed, 
# OR simply instantiate the agents here if we want synchronous execution for the batch (easier for MVP).
# Let's instantiate agents directly to avoid complex chain management inside an agent.
from worker.src.agents.storybook import StorybookAgent
from worker.src.agents.persona_stylist import PersonaStylistAgent
from worker.src.agents.director import DirectorAgent
from worker.src.agents.illustrator import IllustratorAgent
from worker.src.agents.publisher import PublisherAgent
from db.session import get_db
from llm.client import get_llm_client

logger = logging.getLogger(__name__)

class BatchProducerAgent(BaseAgent):
    """
    The Builder.
    Iterates through the Hydrated Graph and executes the creative pipeline for each node.
    Modes: 'text_only' (fast) or 'full_render' (slow, expensive).
    """

    def run_task(self, volume_id: str, mode: str = "text_only", user_id: str = None, universe_ids: Optional[List[str]] = None, target_length: int = 12, storyline_id: Optional[str] = None, is_test_run: bool = False):
        logger.info(f"Batch Producing Volume {volume_id} in mode: {mode}")
        
        # 1. Fetch Volume
        if not user_id:
            vol_res = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
            vol = vol_res.data
            if vol:
                user_id = vol['user_id']
            else:
                logger.error("Volume not found")
                return
        else:
             vol = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute().data

        # 2. Fetch Hydrated Nodes
        try:
            # V4 Fix: Ensure nodes are ordered chronologically so state propagates correctly
            nodes_response = self.db.table("Nodes").select("*").eq("volume_id", volume_id).order("created_at").execute()
            nodes = nodes_response.data
            logger.info(f"Fetched {len(nodes)} nodes for volume {volume_id}.")
        except Exception as e:
            logger.error(f"Error fetching nodes: {e}")
            return

        # Instantiate Agents
        storybook = StorybookAgent(self.db, self.worker, self.llm)
        persona_stylist = PersonaStylistAgent(self.db, self.worker, self.llm)
        director = DirectorAgent(self.db, self.worker, self.llm)
        illustrator = IllustratorAgent(self.db, self.worker, self.llm)
        publisher = PublisherAgent(self.db, self.worker, self.llm)

        # --- PRE-PRODUCTION: DYNAMIC PERSONA ---
        logger.info("Pre-production: Generating dynamic persona for this volume...")
        dynamic_persona = persona_stylist.run_task(user_id=user_id, volume_id=volume_id, universe_ids=universe_ids)

        # --- PRE-PRODUCTION: HIERARCHY OF LAWS & STANCE ---
        final_prohibitions = []
        final_archetype = None
        character_stances = {}
        final_seed_prose = None
        
        universe_id = vol.get('universe_id')
        
        if universe_id:
            try:
                # 1. Fetch Universe to get Active Epoch ID
                uni_res = self.db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
                active_epoch_id = uni_res.data.get('active_epoch_id')
                
                if active_epoch_id:
                    # 2. Fetch Epoch Data (Updated with narrative ledger fields)
                    epoch_res = self.db.table("Epochs").select("archetype, prohibitions, character_stances, seed_prose").eq("id", active_epoch_id).single().execute()
                    epoch_data = epoch_res.data
                    
                    final_archetype = epoch_data.get('archetype')
                    final_prohibitions = epoch_data.get('prohibitions', [])
                    character_stances = epoch_data.get('character_stances', {})
                    final_seed_prose = epoch_data.get('seed_prose')
                    
                    logger.info(f"⚖️ Laws of Physics & Narrative Ledger Loaded for Epoch {active_epoch_id}")
            except Exception as e:
                logger.error(f"Failed to load laws of physics: {e}")

        # NEW: Get Truth Hierarchy Prohibitions for Casting Phase (Merging with Epoch Laws)
        _, casting_prohibitions, casting_anchor, _ = storybook._get_truth_hierarchy_context(user_id, universe_ids, vol.get('root_concept', ''), storyline_id)
        
        # Merge Casting Prohibitions (from Truth Hierarchy) with Epoch Prohibitions
        if casting_prohibitions:
            final_prohibitions = list(set(final_prohibitions + casting_prohibitions))

        casting_prohibitions_str = ""
        if final_prohibitions:
            casting_prohibitions_str = "\n\nSTRICT PROHIBITIONS (The Letter of the Law): DO NOT USE OR REFER TO THESE CONCEPTS:\n" + "\n".join([f"- {p}" for p in final_prohibitions])

        # --- CASTING PHASE (Pre-Production) ---
        graph = vol.get('graph_structure', {})
        master_asset_bank = graph.get('master_asset_bank', {}) or {} # Ensure dict
        visual_style = graph.get('style', 'Graphic Novel') 
        
        # --- GRAND UNIFICATION (Saga Asset Inheritance) ---
        if universe_id:
            try:
                logger.info(f"Checking for Saga Assets in Universe {universe_id}...")
                # Fetch prior volumes in this universe
                prior_vols_res = self.db.table("StoryVolumes").select("graph_structure").eq("universe_id", universe_id).in_("status", ["text_ready", "published"]).lt("created_at", vol.get('created_at', datetime.now(timezone.utc).isoformat())).order("created_at").execute()
                
                inherited_assets = {}
                for pv in prior_vols_res.data:
                    pv_bank = pv.get('graph_structure', {}).get('master_asset_bank', {})
                    if pv_bank:
                        inherited_assets.update(pv_bank)
                
                if inherited_assets:
                    logger.info(f"Inherited {len(inherited_assets)} assets from Saga History.")
                    # Merge: Existing current assets overwrite inherited ones (evolution), 
                    # but usually current bank is empty at this stage.
                    inherited_assets.update(master_asset_bank)
                    master_asset_bank = inherited_assets
                    
                    # Persist the merged bank back to current volume immediately
                    graph['master_asset_bank'] = master_asset_bank
                    self.db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
                    
            except Exception as e:
                logger.warning(f"Saga Asset Inheritance failed: {e}")

        logger.info(f"Checking Casting Phase: Mode={mode}, Existing Bank Size={len(master_asset_bank)}")

        if (mode == "full_render" or mode == "illustrate_only") and not master_asset_bank:
            logger.info("Phase 0: Casting (Generating Master Asset Bank) - Starting...")
            full_story_context = "\n".join([n.get('content', {}).get('summary', '') for n in nodes])
            
            casting_prompt = f"""
            You are the Casting Director. Analyze the entire story summary below.
            
            **CRITICAL UNIVERSE RULE (The Spirit of the Law):**
            {casting_anchor}

            Identify the top 3-5 visual assets (Characters, Artifacts, Locations) that appear repeatedly.
            Create a detailed, immutable visual description for each.
            Output strictly valid JSON: {{ "Name": "Description..." }}
            
            STORY:
            {full_story_context[:2000]}
            {casting_prohibitions_str}
            """
            try:
                resp = self.llm.chat_completion(casting_prompt, json_schema=None)
                if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
                master_asset_bank = json.loads(resp.strip())
                
                if isinstance(master_asset_bank, list):
                    normalized_bank = {}
                    for item in master_asset_bank:
                        if isinstance(item, dict):
                            if "Name" in item and "Description" in item:
                                normalized_bank[item["Name"]] = item["Description"]
                            else:
                                k, v = list(item.items())[0]
                                normalized_bank[k] = v
                    master_asset_bank = normalized_bank

                graph['master_asset_bank'] = master_asset_bank
                self.db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
                logger.info(f"Casting complete. Assets locked: {list(master_asset_bank.keys())}")
            except Exception as e:
                logger.error(f"Casting failed: {e}")
                self.db.table("StoryVolumes").update({"status": "casting_failed"}).eq("id", volume_id).execute()
                return

        # --- V4 STATE CARRIER ---
        current_world_state = {}

        # --- PRODUCTION LOOP ---
        for node in nodes:
            try:
                current_vol_status_res = self.db.table("StoryVolumes").select("status").eq("id", volume_id).single().execute()
                if current_vol_status_res.data and current_vol_status_res.data['status'] in ['draft', 'archived', 'cancelled']:
                    logger.warning(f"Volume {volume_id} status is '{current_vol_status_res.data['status']}'. Aborting production.")
                    return
            except Exception as e:
                logger.warning(f"Could not verify volume status during loop: {e}")

            node_id = node['id']
            content = node.get('content', {})
            status = content.get('production_status', 'pending')

            # MODE 1: TEXT ONLY
            if mode == "text_only":
                if status == 'completed' or status == 'published':
                    logger.info(f"Node {node_id} text already completed. Carrying state.")
                    current_world_state = content.get('ending_state', {})
                    continue
                
                logger.info(f"Executing Storybook for Node {node_id}...")
                try:
                    manifest = storybook.run_task(
                        user_id=user_id, 
                        volume_id=volume_id,
                        node_id=node_id,
                        dynamic_persona=dynamic_persona,
                        assets=master_asset_bank, 
                        universe_ids=universe_ids,
                        target_length=target_length,
                        storyline_id=storyline_id,
                        prohibitions=final_prohibitions,
                        archetype=final_archetype,
                        character_stances=character_stances,
                        seed_prose=final_seed_prose,
                        start_state=current_world_state # <--- V4 HANDOFF
                    )
                    if not manifest: raise ValueError("Storybook returned empty manifest.")
                    
                    # Update Local State Carrier for next iteration
                    current_world_state = manifest.get('ending_state', {})

                    # Preserve existing content and update
                    final_content = content.copy()
                    final_content.update(manifest)
                    final_content['production_status'] = 'completed'
                    
                    self.db.table("Nodes").update({"content": final_content}).eq("id", node_id).execute()
                    logger.info(f"Node {node_id} text generation complete.")
                    
                except Exception as e:
                    logger.error(f"Storybook failed for Node {node_id}: {e}")
                    self.db.table("Nodes").update({"content": {**content, "production_status": "storybook_failed"}}).eq("id", node_id).execute()

            # MODE 2: ILLUSTRATE ONLY
            elif mode == "illustrate_only":
                logger.info(f"Executing Director, Illustrator & Publisher for Node {node_id}...")
                try:
                    director.run_task(node_id=node_id, assets=master_asset_bank, visual_style=visual_style)
                    illustrator.run_task(user_id=user_id, node_id=node_id)
                    publisher.run_task(user_id=user_id, node_id=node_id)
                    logger.info(f"Node {node_id} illustration complete.")
                except Exception as e:
                    logger.error(f"Illustration/Publishing failed for Node {node_id}: {e}")
                    self.db.table("Nodes").update({"content": {**content, "production_status": "render_failed"}}).eq("id", node_id).execute()
            
            # MODE 3: FULL RENDER
            elif mode == "full_render":
                # Step A: Write text if it doesn't exist
                if status != 'completed' and status != 'published':
                    logger.info(f"Executing Storybook for Node {node_id} (Full Render)...")
                    try:
                        manifest = storybook.run_task(
                            user_id=user_id,
                            volume_id=volume_id,
                            node_id=node_id,
                            dynamic_persona=dynamic_persona,
                            assets=master_asset_bank,
                            universe_ids=universe_ids,
                            target_length=target_length,
                            storyline_id=storyline_id,
                            prohibitions=final_prohibitions,
                            archetype=final_archetype,
                            character_stances=character_stances,
                            seed_prose=final_seed_prose,
                            start_state=current_world_state # <--- V4 HANDOFF
                        )
                        if not manifest: raise ValueError("Storybook returned empty manifest.")
                        
                        current_world_state = manifest.get('ending_state', {})
                        content.update(manifest) # Merge new text into existing content
                        content['production_status'] = 'completed' # Mark text as done
                        self.db.table("Nodes").update({"content": content}).eq("id", node_id).execute()
                        logger.info(f"Node {node_id} text generation complete.")
                    except Exception as e:
                        logger.error(f"Storybook failed for Node {node_id} (Full Render): {e}")
                        self.db.table("Nodes").update({"content": {**content, "production_status": "storybook_failed"}}).eq("id", node_id).execute()
                        continue # Don't illustrate if writing failed
                else:
                    # If already written, just carry the state
                    current_world_state = content.get('ending_state', {})

                # Step B: Direct, Illustrate, and Publish
                logger.info(f"Executing Director, Illustrator & Publisher for Node {node_id} (Full Render)...")
                try:
                    # The node content might have been updated, so we re-fetch it for the publisher
                    fresh_node_res = self.db.table("Nodes").select("content").eq("id", node_id).single().execute()
                    if fresh_node_res.data:
                         content = fresh_node_res.data['content']

                    director.run_task(node_id=node_id, assets=master_asset_bank, visual_style=visual_style)
                    illustrator.run_task(user_id=user_id, node_id=node_id)
                    publisher.run_task(user_id=user_id, node_id=node_id) # This now handles the final 'published' status update
                    
                    logger.info(f"Node {node_id} full render complete.")
                except Exception as e:
                    logger.error(f"Illustration/Publishing failed for Node {node_id} (Full Render): {e}")
                    self.db.table("Nodes").update({"content": {**content, "production_status": "render_failed"}}).eq("id", node_id).execute()

        # Finalize the volume, which will set status and trigger crystallization
        # The first argument 'results' is not used in the new flow, so we pass None.
        if not is_test_run:
            from worker.src.agents.tasks import finalize_volume
            finalize_volume.delay(results=None, volume_id=volume_id)
            logger.info(f"Batch Production tasks dispatched. Finalization triggered for Volume {volume_id}.")
