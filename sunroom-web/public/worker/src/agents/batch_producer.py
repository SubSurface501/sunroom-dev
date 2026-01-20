import logging
import time
import json
from .base import BaseAgent
# Import tasks to chain them directly or call agents directly?
# Since BatchProducer is an agent running inside Celery, it can dispatch sub-tasks or run logic.
# To avoid circular imports with tasks.py, we will use the Celery app signature if needed, 
# OR simply instantiate the agents here if we want synchronous execution for the batch (easier for MVP).
# Let's instantiate agents directly to avoid complex chain management inside an agent.
from worker.src.agents.storybook import StorybookAgent
from worker.src.agents.director import DirectorAgent
from worker.src.agents.illustrator import IllustratorAgent
from worker.src.agents.publisher import PublisherAgent
from db.session import get_db
from llm.client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchProducerAgent(BaseAgent):
    """
    The Builder.
    Iterates through the Hydrated Graph and executes the creative pipeline for each node.
    Modes: 'text_only' (fast) or 'full_render' (slow, expensive).
    """

    def run_task(self, volume_id: str, mode: str = "text_only", user_id: str = None):
        logger.info(f"Batch Producing Volume {volume_id} in mode: {mode}")
        
        # 1. Fetch Volume
        # We need user_id if not passed, usually found in volume record
        if not user_id:
            vol_res = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
            vol = vol_res.data
            if vol:
                user_id = vol['user_id']
            else:
                logger.error("Volume not found")
                return
        else:
             # Still fetch vol for graph structure
             vol = self.db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute().data

        # 2. Fetch Hydrated Nodes
        try:
            nodes_response = self.db.table("Trailheads").select("*").eq("volume_id", volume_id).execute()
            nodes = nodes_response.data
            logger.info(f"Fetched {len(nodes)} nodes for volume {volume_id}.")
            # logger.debug(f"Nodes content: {nodes}") # Uncomment for very detailed debug
        except Exception as e:
            logger.error(f"Error fetching nodes: {e}")
            return

        # Instantiate Agents (Synchronous execution for batch stability in this version)
        storybook = StorybookAgent(self.db, self.worker, self.llm)
        director = DirectorAgent(self.db, self.worker, self.llm)
        illustrator = IllustratorAgent(self.db, self.worker, self.llm)
        publisher = PublisherAgent(self.db, self.worker, self.llm)

        # --- CASTING PHASE (Pre-Production) ---
        # Only run if we are in full_render mode or explicitly casting.
        # We check if 'master_asset_bank' exists in the volume's graph_structure.
        graph = vol.get('graph_structure', {})
        if mode == "full_render" and not graph.get('master_asset_bank'):
            logger.info("Phase 0: Casting (Generating Master Asset Bank)...")
            # Collect all node summaries to find characters
            full_story_context = "\n".join([n.get('content', {}).get('summary', '') for n in nodes])
            
            # Use the CAST_EXTRACTION_PROMPT (imported locally or defined here for speed)
            casting_prompt = f"""
            You are the Casting Director. Analyze the entire story summary below.
            Identify the top 3-5 visual assets (Characters, Artifacts, Locations) that appear repeatedly.
            Create a detailed, immutable visual description for each.
            Output strictly valid JSON: {{ "Name": "Description..." }}
            
            STORY:
            {full_story_context[:2000]}
            """
            try:
                resp = self.llm.chat_completion(casting_prompt, json_schema=None)
                # Simple clean
                if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
                elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
                
                master_asset_bank = json.loads(resp.strip())
                
                # Normalize if LLM returns a list
                if isinstance(master_asset_bank, list):
                    normalized_bank = {}
                    for item in master_asset_bank:
                        # Try to find a name/key
                        if isinstance(item, dict):
                            # Heuristic: First key is the name, value is description?
                            # Or look for 'Name' field?
                            if "Name" in item and "Description" in item:
                                normalized_bank[item["Name"]] = item["Description"]
                            else:
                                # Just take the first key-value pair
                                k, v = list(item.items())[0]
                                normalized_bank[k] = v
                    master_asset_bank = normalized_bank

                # Save back to Volume
                graph['master_asset_bank'] = master_asset_bank
                self.db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
                logger.info(f"Casting complete. Assets locked: {list(master_asset_bank.keys())}")
                
            except Exception as e:
                logger.error(f"Casting failed: {e}")

        # --- PRODUCTION LOOP ---
        for node in nodes:
            node_id = node['id']
            status = node.get('content', {}).get('production_status', 'pending')
            
            if status == 'completed' and mode == 'text_only':
                continue # Skip if done
            
            logger.info(f"Processing Node: {node_id} ({node.get('title')})")
            
            # A. WRITING (Storybook)
            # Storybook V2 will automatically look for 'research_dossier' in the node content
            # provided we updated the Storybook logic (which we will check next).
            # Note: Storybook usually generates a FULL SAGA (12 pages) from a single trailhead.
            # For V3 Volume Nodes, we might want a shorter length (e.g., 1-2 pages per node).
            # We'll set target_length=2 for Volume Nodes.
            
            try:
                manifest = storybook.run_task(
                    user_id=user_id, 
                    trailhead_id=node_id, 
                    target_length=2, # Short scenes for branching narrative
                    visual_style="Graphic Novel"
                )
            except Exception as e:
                logger.error(f"Storybook failed for node {node_id}: {e}")
                continue

            # B. RENDERING (Full Render Mode)
            if mode == "full_render":
                try:
                    director.run_task(user_id, node_id)
                    illustrator.run_task(user_id, node_id)
                    # Publisher creates a PDF for this specific node/scene
                    publisher.run_task(user_id, node_id) 
                except Exception as e:
                    logger.error(f"Rendering failed for node {node_id}: {e}")
                    continue
            
            # Update Node Status
            try:
                content = node.get('content', {})
                content['production_status'] = 'completed'
                self.db.table("Trailheads").update({"content": content}).eq("id", node_id).execute()
            except Exception as e:
                logger.error(f"Error updating node status: {e}")
                
        # Update Volume Status
        final_status = "text_ready" if mode == "text_only" else "published"
        self.db.table("StoryVolumes").update({"status": final_status}).eq("id", volume_id).execute()
        logger.info(f"Batch Production Complete. Volume Status: {final_status}")
