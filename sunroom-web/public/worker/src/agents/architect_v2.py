import logging
import json
import uuid
import random
from typing import Dict, List, Any
from .base import BaseAgent
from prompts import VOLUME_ARCHITECT_PROMPT, ARCHITECT_GROWTH_PROMPT
from db import crud, schemas

logger = logging.getLogger(__name__)

class VolumeArchitectAgent(BaseAgent):
    """
    The Deep Weaver.
    Generates a StoryVolume by iteratively growing the graph layer by layer.
    Uses 'Bottleneck Architecture' to manage complexity: Diverges for 2 layers, then Converges to 1.
    """

    def run_task(self, user_id: str, topic: str, depth: int = 6):
        logger.info(f"Designing Deep Volume: {topic} (Depth: {depth})")

        # 1. Generate Root Node
        root_node = self._generate_root(topic)
        if not root_node:
            return None

        nodes = [root_node]
        connections = []
        
        # Track layers for growth
        layers = [[root_node]]

        # 2. Growth Loop
        current_depth = 0
        while current_depth < depth:
            logger.info(f"Growing Layer {current_depth + 1} (Target: {depth})...")
            current_layer = layers[-1]
            next_layer = []
            
            # STRATEGY: Converge every 3rd layer (Depth 2, 5, 8...) to a single bottleneck
            # Depths are 0-indexed. Root is 0.
            # L0(Root) -> Diverge -> L1(2) -> Diverge -> L2(4) -> CONVERGE -> L3(1)
            
            is_bottleneck_step = (current_depth > 0) and ((current_depth + 1) % 3 == 0)
            
            if is_bottleneck_step:
                logger.info(f"--- Bottleneck Step: Converging branches ---")
                bottleneck_node = self._create_bottleneck_node(topic, current_depth)
                nodes.append(bottleneck_node)
                next_layer.append(bottleneck_node)
                
                # Link ALL parents to this single bottleneck
                for parent in current_layer:
                    connection = {
                        "from": parent['node_id'],
                        "to": bottleneck_node['node_id'],
                        "choice_label": "Continue..." # Generic label for convergence
                    }
                    connections.append(connection)
            else:
                # Diverge Step
                logger.info(f"--- Diverge Step: Expanding branches ---")
                for parent in current_layer:
                    # Generate children for this parent
                    children_data = self._grow_branches(parent, topic, current_depth, depth)
                    
                    for child_def in children_data:
                        child_id = f"node_{uuid.uuid4().hex[:8]}"
                        child_node = {
                            "node_id": child_id,
                            "title": child_def.get("child_title", "Untitled"),
                            "type": child_def.get("type", "branch"),
                            "summary": child_def.get("child_summary", "")
                        }
                        
                        connection = {
                            "from": parent['node_id'],
                            "to": child_id,
                            "choice_label": child_def.get("choice_label", "Next")
                        }
                        
                        nodes.append(child_node)
                        connections.append(connection)
                        next_layer.append(child_node)
            
            if not next_layer:
                logger.warning("Growth stopped early: No children generated.")
                break
                
            layers.append(next_layer)
            current_depth += 1

        # 3. Compile Graph Structure
        graph = {
            "nodes": nodes,
            "connections": connections,
            "root_node_id": root_node['node_id']
        }
        
        # 4. Hydrate Real Database Records
        volume_id = self._persist_volume(user_id, topic, graph)
        
        logger.info(f"Volume {volume_id} designed successfully with {len(nodes)} nodes.")
        return volume_id

    def _generate_root(self, topic: str) -> Dict:
        """Creates the single starting point."""
        prompt = f"""
        Design the ROOT node (The Start) for a branching story about: "{topic}".
        Output JSON: {{ "title": "...", "summary": "..." }}
        """
        response = self.llm.chat_completion(prompt, json_schema=None)
        try:
            data = self._parse_json(response)
            return {
                "node_id": "node_root",
                "title": data.get("title"),
                "type": "root",
                "summary": data.get("summary")
            }
        except Exception as e:
            logger.error(f"Root generation failed: {e}")
            return None

    def _create_bottleneck_node(self, topic: str, level: int) -> Dict:
        """Creates a single node that summarizes the convergence of multiple paths."""
        prompt = f"""
        The story paths are converging!
        Topic: {topic}
        Current Level: {level}
        
        Create a "Bottleneck Scene" - a major plot event where all previous choices lead.
        It should be a pivotal moment of realization or confrontation.
        
        Output JSON: {{ "title": "...", "summary": "..." }}
        """
        response = self.llm.chat_completion(prompt, json_schema=None)
        try:
            data = self._parse_json(response)
            return {
                "node_id": f"node_neck_{level}",
                "title": data.get("title"),
                "type": "bottleneck",
                "summary": data.get("summary")
            }
        except Exception as e:
            logger.error(f"Bottleneck generation failed: {e}")
            return {
                "node_id": f"node_neck_{level}",
                "title": "The Convergence",
                "type": "bottleneck",
                "summary": "All paths lead here. The story continues..."
            }

    def _grow_branches(self, parent: Dict, topic: str, current_depth: int, target_depth: int) -> List[Dict]:
        """Asks LLM for 2 choices leading from Parent."""
        prompt = ARCHITECT_GROWTH_PROMPT.format(
            parent_title=parent['title'],
            parent_summary=parent['summary'],
            ancestry_context=f"Topic: {topic}",
            current_depth=current_depth,
            target_depth=target_depth
        )
        
        response = self.llm.chat_completion(prompt, json_schema=None)
        try:
            choices = self._parse_json(response)
            if isinstance(choices, list):
                return choices[:2] 
            return []
        except Exception as e:
            logger.error(f"Branch growth failed for {parent['node_id']}: {e}")
            return []

    def _persist_volume(self, user_id: str, topic: str, graph: Dict) -> str:
        # Create Volume Record
        vol_res = self.db.table("StoryVolumes").insert({
            "user_id": user_id,
            "title": topic,
            "root_concept": topic,
            "graph_structure": graph
        }).execute()
        volume_id = vol_res.data[0]['id']
        print(f"Volume Created: {volume_id}")

        # Create Trailhead Records
        node_id_map = {} 
        
        for node_def in graph['nodes']:
            trailhead = schemas.TrailheadCreate(
                user_id=user_id,
                volume_id=volume_id, # Correctly linked
                title=node_def['title'],
                insight=f"Node in Volume {topic}",
                suggested_topic=node_def['title'],
                type="story_node",
                content={
                    "summary": node_def['summary'],
                    "blueprint_id": node_def['node_id'],
                    "type": node_def['type']
                }
            )
            th_res = crud.create_trailhead(self.db, trailhead)
            node_id_map[node_def['node_id']] = th_res.id
            
        # Update Volume with the ID Map
        graph['node_id_map'] = node_id_map
        self.db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
        
        return volume_id

    def _parse_json(self, text: str):
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
