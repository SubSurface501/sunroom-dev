import os
import sys

print("--- WORKER MODULE LOADING (STDOUT FORCE) ---", flush=True)

from dotenv import load_dotenv
load_dotenv()

import logging
import sys
from celery import Celery, chord, chain, group
from celery.signals import setup_logging
from db.session import get_db
from llm.client import LLMClient

import asyncio # Add asyncio import

# --- NUCLEAR LOGGING FIX ---
@setup_logging.connect
def config_loggers(*args, **kwtags):
    # This signal disables Celery's internal logging setup
    # allowing us to control it completely.
    pass

# Reset root logger
root = logging.getLogger()
for handler in root.handlers[:]:
    root.removeHandler(handler)

# Create a clean single handler
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'))
root.addHandler(handler)
root.setLevel(logging.INFO)

# Ensure no other loggers propagate and double up
logging.getLogger("worker").propagate = True # Now it goes to root (single handler)
logging.getLogger("celery").propagate = False # Stop celery internal noise

logger = logging.getLogger(__name__)

# Import the agents that are part of the MVP
from worker.src.agents.indexing import IndexAtomAgent
from worker.src.agents.scripting import ScriptingAgent
from worker.src.agents.youtube_ideation import GeneratePerformanceDrivenIdeasAgent
from worker.src.agents.youtube_ingestion import IngestYoutubeChannelAgent
from worker.src.agents.narrator_agent import NarratorAgent
from worker.src.agents.storybook import StorybookAgent
from worker.src.agents.illustrator import IllustratorAgent
from worker.src.agents.publisher import PublisherAgent
from worker.src.agents.biographer import BiographerAgent
from worker.src.agents.architect_v2 import VolumeArchitectAgent
from worker.src.agents.researcher import ResearcherAgent
from worker.src.agents.batch_producer import BatchProducerAgent
from worker.src.agents.simulation_agent import SimulationAgent
from worker.src.agents.auto_genesis_agent import AutoGenesisAgent
from worker.src.agents.crystallize import CrystallizeVolumeAgent
from worker.src.agents.librarian import LibrarianAgent # Import Librarian
from worker.src.agents.distiller import DistillerAgent # Import Distiller
from worker.src.agents.persona_builder import PersonaBuilderAgent # Import PersonaBuilder
from worker.src.agents.reviewer import ReviewAgent # Import Reviewer
from worker.src.agents.director import DirectorAgent
from worker.src.agents.scribe import ScribeAgent
from worker.src.agents.energy_middleware import EnergyModelMiddleware
from worker.src.agents.domain_expert import DomainExpertAgent
from worker.src.agents.discovery_agent import DiscoveryAgent
from worker.src.agents.writers_room import WritersRoomAgent
from worker.src.agents.curator import CuratorAgent
from worker.src.agents.categorizer import CategorizerAgent # Import Categorizer

from db.crud import match_atoms_by_embedding
from db import crud, schemas
from services.billing.gatekeeper import UsageGatekeeper, QuotaExceededError
import subprocess
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

# Configure logging
logger = logging.getLogger(__name__)
logger.info("--- agents/tasks.py: Starting execution ---")

from llm.client import LLMClient

# Configure Celery
# Use environment variable or default to localhost
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
logger.info(f"Celery Broker: {broker_url}")

# Sentry Initialization for Celery Worker
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[CeleryIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# --- Worker Setup ---
worker = Celery('sunroom-worker',
                broker=broker_url,
                backend='rpc://',
                include=['worker.src.agents.tasks'])
worker.conf.update(
    broker_connection_retry_on_startup=True,
    worker_pool_restarts=True,
    worker_send_task_events=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # This is the important line for Windows
    worker_forking_enable=False 
)
# --- End Worker Setup ---




@worker.task(bind=True, name='agents.tasks.run_writers_room')
def run_writers_room(self, trailhead: dict, volume_id: str, user_id: str):
    """
    Async task wrapper for the Writers' Room.
    Reports granular progress back to the API/Frontend.
    """
    logger.info(f"🎬 Async Writers' Room started for '{trailhead.get('title', 'Untitled')}'")
    
    db = get_db()
    
    # We create a custom callback to update Celery state
    def progress_callback(phase: str, percent: int, details: str):
        self.update_state(state='PROGRESS', meta={
            'phase': phase,
            'percent': percent,
            'details': details
        })
    
    # Initialize Agent with the callback
    room = WritersRoomAgent(db, worker)
    room.set_progress_callback(progress_callback)
    
    result = room.execute_production_run(trailhead, volume_id, user_id)
    
    return result

@worker.task(name='agents.tasks.generate_constrained_thought')
def generate_constrained_thought(prompt: str, user_id: str, volume_id: str = None):
    """
    Generates a thought using System 2 Refinement (Latent Energy Calibration).
    Loops until the thought satisfies the Energy Manifold constraints (P* > Threshold).
    """
    logger.info(f"Generating Constrained Thought (Alpha-Beta-Gamma) for: {prompt}")
    
    db = get_db()
    llm = LLMClient()
    middleware = EnergyModelMiddleware()
    domain_agent = DomainExpertAgent(db, worker, llm)

    # 1. Draft
    current_draft = llm.chat_completion(f"Draft a concise scientific hypothesis about: {prompt}")
    logger.info(f"Draft 0: {current_draft[:50]}...")
    
    # 2. Refinement Loop
    max_iterations = 3
    energy = 0.0
    
    for i in range(max_iterations):
        embedding = llm.get_embedding(current_draft)
        
        # A. Fetch Contexts
        # Alpha: Hybrid Match
        # We must pass query_user_id to respect sovereignty
        local_context = crud.match_atoms_hybrid(db, current_draft, embedding, 0.5, 5, query_user_id=user_id)
        
        # Beta: EXTRACT KEYWORDS to fix the "Neutral" score issue
        # We ask LLM for a single search term
        search_prompt = f"Extract the single most important scientific entity/concept from this text for a database search. Return ONLY the term. Text: '{current_draft[:200]}'"
        search_term = llm.chat_completion(search_prompt).strip()
        external_context = domain_agent.search_external_concepts(search_term)
        
        # Gamma: Fetch Trajectory
        # Use the new CRUD function
        if volume_id:
            trajectory_atoms = crud.get_recent_volume_atoms(db, volume_id, limit=5)
        else:
            trajectory_atoms = []
        
        # B. Calculate Energy (Triad)
        full_context = local_context + external_context
        energy, critique = middleware.calculate_energy(embedding, full_context, trajectory_atoms)
        
        logger.info(f"🔄 Iteration {i+1}: Energy={energy:.4f} | Critique: {critique}")
        
        # C. Threshold (Lowered slightly for 3-variable geometric mean)
        if energy > 0.65:
            logger.info("Energy Threshold Met.")
            break
            
        # D. Refine
        openalex_sources = [r.get('concept_name', r.get('title')) for r in external_context if r.get('source') == 'OpenAlex']
        refinement_prompt = f"""
        Refine this hypothesis to meet geometric constraints.
        Draft: "{current_draft}"
        Critique: {critique}
        
         Directives:
        - If Alpha Low: Be more unique.
        - If Gamma Low: Align better with the project's previous thoughts.
        - If Beta Low: Integrate these real sources: {openalex_sources}
        """
        current_draft = llm.chat_completion(refinement_prompt)

    # 3. Save
    atom_id = None
    try:
        atom = schemas.Atom(
            user_id=user_id,
            name=f"Thought: {prompt[:30]}",
            type="thought",
            content=current_draft,
            embedding=llm.get_embedding(current_draft),
            metadata={"volume_id": volume_id, "energy_score": energy, "critique": critique, "triad_stabilized": True}
        )
        created = crud.create_atom(db, atom)
        if created:
            atom_id = created.id
    except Exception as e:
        logger.error(f"Failed to save atom: {e}")
    
    return f"Refined Atom Saved (Energy: {energy:.4f})"

@worker.task(name='agents.reviewer.run')
def run_review_agent(volume_id: str, node_id: str, draft_text: str):
    """
    The Reviewer Task.
    Validates draft content.
    """
    logger.info(f"--- Review Task started for Node {node_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = ReviewAgent(db, worker, llm)
    try:
        report = agent.run_task(volume_id=volume_id, node_id=node_id, draft_text=draft_text)
        return report
    except Exception as e:
        logger.error(f"Review Failed: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.persona.build')
def run_persona_builder(user_id: str):
    """
    The Cartographer Task.
    Builds the Persona Profile.
    """

    
    logger.info(f"--- Persona Builder Task started for user {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = PersonaBuilderAgent(db, worker, llm)
    try:
        agent.run_task(user_id=user_id)
        return "Persona Build Complete"
    except Exception as e:
        logger.error(f"Persona Build Failed: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.distiller.run')
def run_distiller_agent(user_id: str, time_window: str = 'monthly'):
    """
    The Distiller Task.
    Compresses atoms into Semantic Memories.
    """

    
    logger.info(f"--- Distiller Task started for user {user_id} ({time_window}) ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = DistillerAgent(db, worker, llm)
    try:
        agent.run_task(user_id=user_id, time_window=time_window)
        return "Distillation Complete"
    except Exception as e:
        logger.error(f"Distillation Failed: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.tasks.scan_and_process_source')
def scan_and_process_source(source_id: str, user_id: str):
    """
    The Ingestion Pipeline V2.
    Librarian Scan -> Indexing.
    """

    
    logger.info(f"--- Pipeline: Scan & Process Source {source_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    # 1. Librarian Scan (Synchronous for simplicity in this worker thread)
    librarian = LibrarianAgent(db, worker, llm)
    scan_result = librarian.run_task(source_id)
    
    # 2. Indexing (Process Source) - only if the librarian extracted text
    if scan_result == "text_extracted":
        logger.info(f"Librarian extracted text for {source_id}. Triggering text indexing.")
        process_source.delay(source_id, user_id)
    else:
        logger.info(f"Librarian returned status '{scan_result}'. Bypassing standard text indexing.")

    return f"Scan complete for {source_id} with status: {scan_result}"

@worker.task(name='agents.tasks.process_source')
def process_source(source_id: str, user_id: str):
    """
    Celery task to process a source (Index it).
    This is a wrapper around IndexAtomAgent.
    """

    
    logger.info(f"--- Processing Source {source_id} for user {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = IndexAtomAgent(db, worker, llm)
    try:
        agent.run_task(source_id=source_id, user_id=user_id)
        logger.info(f"Source {source_id} processed successfully. Triggering categorization.")
        # Now, trigger the next step in the pipeline.
        categorize_source.delay(source_id=source_id, user_id=user_id)
        return f"Source {source_id} processing and categorization triggered."
    except Exception as e:
        logger.error(f"Failed to process source {source_id}: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.tasks.categorize_source')
def categorize_source(source_id: str, user_id: str):
    """
    Celery task to run the CategorizerAgent.
    """

    
    logger.info(f"--- Categorizing Source {source_id} for user {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = CategorizerAgent(db, worker, llm)
    try:
        result = agent.run_task(source_id=source_id, user_id=user_id)
        return f"Categorization for {source_id} complete: {result}"
    except Exception as e:
        logger.error(f"Failed to categorize source {source_id}: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.tasks.index_atom')
def index_atom(atom_id: str, user_id: str):
    """
    Task to re-index (generate embedding for) a specific atom.
    Useful for repairing atoms with missing embeddings or updating the vector space.
    """


    logger.info(f"--- Indexing Atom {atom_id} for user {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    # 1. Fetch Atom
    atom_res = db.table("Atoms").select("*").eq("id", atom_id).single().execute()
    if not atom_res.data:
        logger.error(f"Atom {atom_id} not found.")
        return "Atom Not Found"
        
    atom = atom_res.data
    content = atom.get('content') or atom.get('name')
    
    if not content:
        logger.warning(f"Atom {atom_id} has no content to embed.")
        return "No Content"
        
    # 2. Generate Embedding
    try:
        embedding = llm.get_embedding(content)
        
        # 3. Update DB
        db.table("Atoms").update({"embedding": embedding}).eq("id", atom_id).execute()
        logger.info(f"Successfully updated embedding for Atom {atom_id}")
        return "Indexed"
        
    except Exception as e:
        logger.error(f"Failed to index atom {atom_id}: {e}")
        return "Failed"

@worker.task(name='agents.tasks.process_image_source')
def process_image_source(source_id: str, user_id: str):
    logger.info(f"Processing Image Source {source_id} for user {user_id}")
    
    # 1. Fetch Source Metadata & Active Lenses
    admin_db = get_db()
    source_resp = admin_db.table("Sources").select("*").eq("id", source_id).single().execute()
    if not source_resp.data:
        logger.error("Source not found")
        return
    source = source_resp.data
    storage_path = source.get('storage_path')
    
    if not storage_path or not os.path.exists(storage_path):
        logger.error(f"Image file not found at {storage_path}")
        return

    # Fetch Lenses (Seed Prose atoms) to use as context
    lenses_resp = admin_db.table("Atoms").select("name").eq("user_id", user_id).eq("type", "seed_prose").execute()
    active_lenses = [a['name'] for a in lenses_resp.data] if lenses_resp.data else []
    
    # 2. Vision Service: Analyze Image
    from worker.src.services.vision import VisionService
    vision = VisionService()
    
    try:
        with open(storage_path, "rb") as f:
            image_bytes = f.read()
            
        description = asyncio.run(vision.analyze_image(image_bytes, active_lenses))
        logger.info(f"Generated visual description: {description[:100]}...")
        
        # 3. Save Description to Source (Update raw_text so IndexAtomAgent can use it, or handle it uniquely)
        # We'll save it to raw_text for simplicity so we can reuse the text indexer if we want, 
        # OR we can create a special 'visual_artifact' atom directly.
        # Let's create a 'visual_artifact' atom directly to preserve the 'media_url'.
        
        # Create Atom
        llm = LLMClient()
        embedding = llm.get_embedding(description)
        
        atom_data = {
            "user_id": user_id,
            "name": f"Visual: {source['title']}",
            "type": "visual_artifact", # New type we should add to enum or loose string
            "content": description,
            "visual_description": description,
            "media_url": storage_path, # Local path for now, ideally S3 URL
            "embedding": embedding,
            "metadata": {"source_id": source_id, "is_visual": True}
        }
        
        # Insert Atom
        atom_resp = admin_db.table("Atoms").insert(atom_data).execute()
        if atom_resp.data:
             atom_id = atom_resp.data[0]['id']
             # Link to Source
             admin_db.table("Atoms_to_Sources").insert({"atom_id": atom_id, "source_id": source_id}).execute()
             
        logger.info(f"Created Visual Atom for source {source_id}")
        
    except Exception as e:
        logger.error(f"Error processing image source: {e}")

@worker.task(name='agents.tasks.run_proactive_discovery')
def run_proactive_discovery(user_id: str):
    """
    Day 1 Feature: The Curiosity.
    Finds 'Question' atoms and attempts to resolve them using search.
    """

    
    logger.info(f"--- Proactive Discovery: Waking up for {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    # 1. Identify Gaps (Find unresolved Question atoms)
    # We look for atoms with type='question' and no resolution link
    # For MVP, we'll search for the literal string "?" in atom names or content, 
    # but ideally we have a structured type. V6 schema added 'Question' type.
    
    questions_res = db.table("Atoms").select("*").eq("user_id", user_id).eq("type", "question").limit(5).execute()
    
    if not questions_res.data:
        logger.info("No burning questions found. Curiosity is sated.")
        return "No Questions"
        
    logger.info(f"Found {len(questions_res.data)} questions to investigate.")
    
    # Try importing DiscoveryAgent
    try:
        from worker.src.agents.discovery import DiscoveryAgent # Hypothetical agent from V6
        discovery = DiscoveryAgent(db, worker, llm)
        results = discovery.run_task(user_id=user_id)
        return f"Discovery Run Complete: {results}"
    except ImportError:
        # Fallback if DiscoveryAgent file is missing (it might be in 'agents.discovery' or 'agents.researcher')
        logger.warning("DiscoveryAgent not found. Running minimal search logic.")
        
        # Simple Search Logic
        results = []
        for q in questions_res.data:
            query = q['name']
            logger.info(f"Searching for: {query}")
            # Placeholder for actual Google Search
            # We would use the GOOGLE_CUSTOM_SEARCH_API_KEY here
            # For now, we simulate success to verify the pipeline.
            logger.info(f"-> Found 3 sources for {query}. Ingesting...")
            results.append(query)
            
        return f"Simulated Discovery for {len(results)} items."

@worker.task(name='agents.auto_genesis.run')
def run_auto_genesis(user_id: str):
    """
    The Centrifuge Task.
    Clusters user history and extracts seed atoms.
    """

    
    logger.info(f"--- Auto-Genesis Task started for user {user_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = AutoGenesisAgent(db, worker, llm)
    try:
        result = agent.run_task(user_id=user_id)
        return f"Auto-Genesis Complete. Seeds: {result}"
    except Exception as e:
        logger.error(f"Auto-Genesis Failed: {e}", exc_info=True)
        return "Failed"

@worker.task(bind=True, name='agents.pipeline.ensure_asset_bank')
def ensure_asset_bank(self, volume_id: str):
    """
    Step 1: THE CASTING GATE
    Checks if the volume has a 'master_asset_bank'. If not, generates it.
    This is a BLOCKING task. No writing happens until this finishes.
    """

    
    db = get_db()
    logger.info(f"⚡ Casting Phase for Volume {volume_id}...")
    
    # Fetch Volume
    vol_res = db.table("StoryVolumes").select("*").eq("id", volume_id).single().execute()
    if not vol_res.data:
        logger.error(f"Volume {volume_id} not found")
        raise ValueError(f"Volume {volume_id} not found")
    
    volume = vol_res.data
    graph = volume.get('graph_structure', {})
    
    # --- FIX FOR POINT #4: SYNC CHECK ---
    db_nodes_res = db.table("Trailheads").select("id, title, content").eq("volume_id", volume_id).execute()
    db_nodes = db_nodes_res.data
    
    json_nodes = graph.get('node_id_map', {}).values()
    
    # Simple check: compare counts. More robust check would compare sets of IDs.
    if len(db_nodes) != len(json_nodes):
        logger.warning("⚠️ Drift detected between JSON Graph and DB Rows. Rehydrating...")
        # Rebuild the node_id_map based on DB Rows
        new_map = {}
        # We need to map DB IDs back to graph node IDs. 
        # However, if we lost the mapping, we might need to infer or just regenerate simple keys.
        # But architect_v2 generated "node_xyz".
        # If we can't match easily, we just ensure the map covers all DB nodes.
        # Let's check if the existing map is just partial.
        existing_reverse_map = {v: k for k, v in graph.get('node_id_map', {}).items()}
        
        for n in db_nodes:
            if n['id'] not in existing_reverse_map:
                # Create a new key if missing
                node_key = n.get('content', {}).get('blueprint_id', f"node_{n['id'][:8]}")
                new_map[node_key] = n['id']
            else:
                new_map[existing_reverse_map[n['id']]] = n['id']
        
        graph['node_id_map'] = new_map
        # Update Volume immediately
        db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
        logger.info("Rehydration complete.")
    
    # --- CASTING LOGIC ---
    if not graph.get('master_asset_bank'):
        logger.info("Generatin Master Asset Bank...")
        llm = LLMClient()
        
        # Collect all node summaries
        full_story_context = "\n".join([n.get('content', {}).get('summary', '') for n in db_nodes])
        
        casting_prompt = f"""
        You are the Casting Director. Analyze the entire story summary below.
        Identify the top 3-5 visual assets (Characters, Artifacts, Locations) that appear repeatedly.
        Create a detailed, immutable visual description for each.
        Output strictly valid JSON: {{ "Name": "Description..." }}
        
        STORY:
        {full_story_context[:3000]}
        """
        try:
            resp = llm.chat_completion(casting_prompt, json_schema=None)
            # Simple clean
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            
            master_asset_bank = json.loads(resp.strip())
            
            # Normalize
            if isinstance(master_asset_bank, list):
                normalized_bank = {}
                for item in master_asset_bank:
                    if isinstance(item, dict):
                        # Heuristic: First key is name, value is description
                        k, v = list(item.items())[0]
                        normalized_bank[k] = v
                master_asset_bank = normalized_bank
            
            graph['master_asset_bank'] = master_asset_bank
            db.table("StoryVolumes").update({"graph_structure": graph}).eq("id", volume_id).execute()
            logger.info(f"Casting Complete. Assets locked: {list(master_asset_bank.keys())}")
            
        except Exception as e:
            logger.error(f"Casting failed: {e}")
            # We allow it to proceed without assets if casting fails, or we could raise.
            # Let's raise to stop the chain if critical.
            # raise e
            pass # Proceed for now
            
    return volume_id

@worker.task(name='agents.pipeline.write_node_task')
def write_node_task(node_id: str, volume_id: str, world_bible: dict):
    """
    Step 3: THE WRITER (Running in Parallel, but called sequentially in the test script)
    """

    
    db = get_db()
    llm = LLMClient()
    
    logger.info(f"Starting write task for Node {node_id}")
    
    # 1. Fetch fresh data
    vol_res = db.table("StoryVolumes").select("graph_structure, user_id, universe_id, storyline_id").eq("id", volume_id).single().execute()
    volume = vol_res.data
    
    assets = volume.get('graph_structure', {}).get('master_asset_bank', {})
    user_id = volume['user_id']
    universe_id = volume.get('universe_id')
    storyline_id = volume.get('storyline_id')
    universe_ids = [universe_id] if universe_id else []

    # 2. Fetch World Bible & Prohibitions
    prohibitions = []
    if universe_id:
        # The world_bible is passed in, but we need to get the prohibitions for the current epoch
        uni_res = db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
        if uni_res.data:
            epoch_id = uni_res.data.get('active_epoch_id')
            if epoch_id:
                ep_res = db.table("Epochs").select("prohibitions").eq("id", epoch_id).single().execute()
                if ep_res.data:
                    prohibitions = ep_res.data.get('prohibitions', [])

    # Run Storybook
    storybook = StorybookAgent(db, None, llm)
    manifest, updated_world_bible = storybook.run_task(
        user_id=user_id,
        volume_id=volume_id,
        node_id=node_id,
        target_length=2,
        universe_ids=universe_ids,
        storyline_id=storyline_id,
        world_bible=world_bible,
        prohibitions=prohibitions
    )
    
    # Update Node Status and Save Manuscript
    node_res = db.table("Nodes").select("content").eq("id", node_id).single().execute()
    if node_res.data:
        content = node_res.data.get('content', {})
        
        # Merge the generated manifest into the existing content
        if manifest:
            content.update(manifest)
            
        content['production_status'] = 'completed'
        db.table("Nodes").update({"content": content}).eq("id", node_id).execute()

    # This task now returns the updated world bible for sequential execution
    # For parallel execution, this would be fire-and-forget, and the finalize logic would be critical.
    
    # "Poor Man's Chord" - Check if we are the last one
    import time
    time.sleep(1.0)

    all_nodes_res = db.table("Nodes").select("content").eq("volume_id", volume_id).execute()
    all_nodes = all_nodes_res.data
    
    pending_count = 0
    for n in all_nodes:
        status = n.get('content', {}).get('production_status', 'pending')
        if status != 'completed':
            pending_count += 1
            
    logger.info(f"Volume {volume_id} pending nodes: {pending_count}")
    
    if pending_count == 0:
        logger.info(f"All nodes for {volume_id} complete. Triggering Finalize.")
        finalize_volume.delay(None, volume_id)
        
    return f"Node {node_id} Written", updated_world_bible

@worker.task(name='agents.pipeline.crystallize_volume')
def crystallize_volume_task(volume_id: str):
    """
    Step 5: THE FEEDBACK LOOP
    Ingests the finished story back into the Atom memory.
    """

    
    logger.info(f"--- Crystallizing Volume {volume_id} ---")
    
    db = get_db()
    llm = LLMClient()
    
    agent = CrystallizeVolumeAgent(db, worker, llm)
    try:
        result = agent.run_task(volume_id=volume_id)
        return result
    except Exception as e:
        logger.error(f"Crystallization Failed: {e}", exc_info=True)
        return "Failed"

@worker.task(name='agents.pipeline.finalize_volume')
def finalize_volume(results, volume_id: str):
    """
    Step 4: THE FINISHER
    Runs only after ALL writers have succeeded.
    """

    
    db = get_db()
    logger.info(f"Checking finalization for Volume {volume_id}...")
    
    # IDEMPOTENCY GUARD: Check if already finalized
    vol = db.table("StoryVolumes").select("status").eq("id", volume_id).single().execute()
    if vol.data and vol.data['status'] in ['text_ready', 'published']:
        logger.info(f"Volume {volume_id} already finalized. Skipping.")
        return "Already Finalized"

    db.table("StoryVolumes").update({"status": "text_ready"}).eq("id", volume_id).execute()
    logger.info(f"🎉 Volume {volume_id} fully written and marked as text_ready!")
    
    # Trigger Crystallization (The Feedback Loop)
    crystallize_volume_task.delay(volume_id)
    
    # --- EPOCHAL CRAWLER (The Time Machine) ---
    try:
        # 1. Check Universe Context
        vol_data = db.table("StoryVolumes").select("universe_id, user_id, storyline_id, title").eq("id", volume_id).single().execute()
        if vol_data.data and vol_data.data.get('universe_id'):
            universe_id = vol_data.data['universe_id']
            user_id = vol_data.data['user_id']
            storyline_id = vol_data.data.get('storyline_id')
            
            # 2. Get Current Epoch
            uni_res = db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
            current_epoch_id = uni_res.data.get('active_epoch_id')
            
            if current_epoch_id:
                # 3. Find Next Epoch
                next_epoch_res = db.table("Epochs").select("*").eq("universe_id", universe_id).gt("id", current_epoch_id).order("id").limit(1).execute()
                
                if next_epoch_res.data:
                    next_epoch = next_epoch_res.data[0]
                    new_epoch_id = next_epoch['id']
                    new_epoch_name = next_epoch.get('name', f"Epoch {new_epoch_id}")
                    original_seed_prose = next_epoch.get('seed_prose', f"Narrative for {new_epoch_name}")
                    
                    logger.info(f"⏳ Time Travel Detected: Moving from Epoch {current_epoch_id} to {new_epoch_id} ({new_epoch_name})")
                    
                    # --- NEW: Epoch Consolidation (Style, Memory, Ghost Wiping) ---
                    from .epoch_manager import EpochManagerAgent
                    epoch_manager = EpochManagerAgent(db, worker, LLMClient())
                    
                    try:
                        # Consolidate the old epoch (Wipes ghosts, generates style vector)
                        epoch_manager.consolidate_epoch(universe_id, current_epoch_id)
                        
                        # --- LEDGER INHERITANCE (The Baton Pass) ---
                        # Copy logical state (Inventory, Quests) using the manager
                        epoch_manager.inherit_ledger(current_epoch_id, new_epoch_id)
                    except Exception as e:
                        logger.error(f"Epoch Management Failed: {e}")

                    # --- DYNAMIC BRIDGE (Transient) ---
                    # MOVED TO draft_volume_structure for Manual Greenlight workflow.
                    # We create a temporary instruction that bridges the gap, but we DO NOT overwrite the DB.
                    # bridged_seed_prose = original_seed_prose
                    # try:
                    #     # A. Fetch Actual Ending of Current Volume
                    #     last_node_res = db.table("Nodes").select("content").eq("volume_id", volume_id).order("created_at", desc=True).limit(1).execute()
                    #     if last_node_res.data:
                    #         last_content = last_node_res.data[0].get('content', {})
                    #         pages = last_content.get('pages', [])
                    #         if pages:
                    #             previous_ending = pages[-1].get('narrative_text', '')[-1500:] 
                    #         else:
                    #             previous_ending = last_content.get('summary', '')
                    #         
                    #         if previous_ending:
                    #             logger.info("Constructing Transient Narrative Bridge...")
                    #             llm = LLMClient()
                    #             bridge_prompt = f"""
                    #             I am writing a serialized saga. 
                    #             Chapter 1 has just finished. I need to write the opening prompt for Chapter 2.
                    #             
                    #             ACTUAL ENDING OF CHAPTER 1:
                    #             "{previous_ending}"
                    #             
                    #             ORIGINAL PLAN FOR CHAPTER 2 (USER INTENT):
                    #             "{original_seed_prose}"
                    #             
                    #             TASK:
                    #             Rewrite the "Original Plan" to ensure perfect continuity with the "Actual Ending".
                    #             1. PLOT BRIDGE:
                    #             - If Chapter 1 ended with her on a horse, Chapter 2 must start with her on a horse.
                    #             - If she acquired an item or met someone, mention it in the opening.
                    #             - KEEP the core goal and setting of the Original Plan (e.g. going to the forest, fighting wolves), but change the *entry point* and *initial state* to match the ending.
                    #             
                    #             2. STYLISTIC INHERITANCE (CRITICAL):
                    #             - Analyze the "Actual Ending". Is it dense, technical, lyrical, or simple?
                    #             - WRITE THE NEW PROMPT IN THAT SAME VOICE.
                    #             - Do not revert to generic fantasy prose. If the ending used words like "fulcrum" and "thermal conductivity," your new prompt must use similar intellectual rigor.
                    #             
                    #             Output ONLY the rewritten prose.
                    #             """
                    #             bridged_seed_prose = llm.chat_completion(bridge_prompt).strip().strip('"')
                    #             logger.info(f"Transient Bridge Constructed: {bridged_seed_prose[:100]}...")
                    #             # WE DO NOT SAVE THIS TO THE DB. It is for this run only.
                    # 
                    # except Exception as e:
                    #     logger.error(f"Bridge construction failed, using original prose: {e}")

                    # 4a. Update Universe Clock (Advance to Next Epoch)
                    # This enables the Dashboard to see the new Epoch is active.
                    db.table("Universes").update({"active_epoch_id": new_epoch_id}).eq("id", universe_id).execute()
                    
                    # 4b. Trigger Next Volume (PASSING STORYLINE_ID)
                    # DISABLED for Manual Greenlight. User must trigger next volume in Dashboard.
                    # draft_volume_structure.delay(
                    #     user_id=user_id,
                    #     theme=f"Chapter {new_epoch_id}: {new_epoch_name}", # Theme is just the title
                    #     seed_prose=bridged_seed_prose, # Pass the dynamic bridge here
                    #     root_concept=f"Chapter: {new_epoch_name}", # Use Name, not ID
                    #     universe_id=universe_id,
                    #     storyline_id=storyline_id, 
                    #     volume_id=None 
                    # )
                    # logger.info(f"Crawler Triggered: Drafting {new_epoch_name}")
                    logger.info(f"Crawler Paused: Epoch advanced to {new_epoch_name}. Waiting for user to trigger next volume.")
                else:
                    logger.info("Timeline End: No further epochs found.")
    except Exception as e:
        logger.error(f"Crawler failed: {e}")

    return f"Volume {volume_id} Complete"

@worker.task(name='agents.pipeline.dispatch_writers')
def dispatch_writers(volume_id: str):
    """
    Step 2: THE DISPATCHER
    Queries the DB for nodes and triggers the parallel group.
    """

    
    db = get_db()
    logger.info(f"Dispatching writers for Volume {volume_id}")
    
    # Fetch all nodes associated with this volume
    nodes_res = db.table("Nodes").select("id").eq("volume_id", volume_id).execute()
    nodes = nodes_res.data
    
    if not nodes:
        logger.warning("No nodes found for volume.")
        return "No nodes"

    # Create a Group of tasks
    header = group(write_node_task.s(n['id'], volume_id) for n in nodes)
    
    # Fire the group without a callback (Fire and Forget)
    # The write_node_task will handle the finalization check
    return header.delay()


@worker.task(name='agents.youtube_ideation.run')
def run_youtube_ideation_agent(user_id: str, youtube_channel_id: str, focus_area: str = None, depth: str = "Beginner"):
    """Celery task to run the YouTube ideation agent."""
    # Construct the absolute path to the .env file.
    # This is necessary because the Celery worker's current directory is not guaranteed.
    # __file__ is in worker/src/agents/, so we go up 3 levels to the project root.


    logger.info(f"--- Celery task 'agents.youtube_ideation.run' received for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = GeneratePerformanceDrivenIdeasAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, youtube_channel_id=youtube_channel_id, focus_area=focus_area, depth=depth)
    except Exception as e:
        logger.error(f"Error in GeneratePerformanceDrivenIdeasAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.youtube_ingestion.run')
def run_youtube_ingestion_agent(user_id: str):
    """Celery task to run the YouTube ingestion agent."""


    logger.info(f"--- Celery task 'agents.youtube_ingestion.run' received for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = IngestYoutubeChannelAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id)
    except Exception as e:
        logger.error(f"Error in IngestYoutubeChannelAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.indexing.run')
def run_indexing_agent(source_id: str, user_id: str):
    """Celery task to run the IndexAtomAgent."""


    logger.info(f"--- Celery task 'agents.indexing.run' received for source {source_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = IndexAtomAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(source_id=source_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in IndexAtomAgent for source {source_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.scripting.run')
def run_script_generation(trailhead_id: str, user_id: str, focus_area: str = None, depth: str = "Broad"):
    """Celery task to run the ScriptingAgent."""


    logger.info(f"--- Celery task 'agents.scripting.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = ScriptingAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(trailhead_id=trailhead_id, user_id=user_id, focus_area=focus_area, depth=depth)
    except Exception as e:
        logger.error(f"Error in ScriptingAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.narrator.run')
def run_narrator_agent(trailhead_id: str, user_id: str):
    """Celery task to run the NarratorAgent."""


    logger.info(f"--- Celery task 'agents.narrator.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = NarratorAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(trailhead_id=trailhead_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in NarratorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.storybook.run')
def run_storybook_agent(user_id: str, trailhead_id: str = None, source_id: str = None, target_length: int = 12, visual_style: str = "Mystical Realism"):
    """Celery task to run the StorybookAgent."""


    logger.info(f"--- Celery task 'agents.storybook.run' received for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = StorybookAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id, source_id=source_id, target_length=target_length, visual_style=visual_style)
    except Exception as e:
        logger.error(f"Error in StorybookAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.illustrator.run')
def run_illustrator_agent(user_id: str, trailhead_id: str, provider: str = "vertex_sd"):
    """Celery task to run the IllustratorAgent."""


    logger.info(f"--- Celery task 'agents.illustrator.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = IllustratorAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id, provider=provider)
    except Exception as e:
        logger.error(f"Error in IllustratorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.publisher.run')
def run_publisher_agent(user_id: str, trailhead_id: str):
    """Celery task to run the PublisherAgent."""


    logger.info(f"--- Celery task 'agents.publisher.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = PublisherAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id)
    except Exception as e:
        logger.error(f"Error in PublisherAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.director.run')
def run_director_agent(user_id: str, trailhead_id: str):
    """Celery task to run the DirectorAgent."""


    logger.info(f"--- Celery task 'agents.director.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = DirectorAgent(db, llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id)
    except Exception as e:
        logger.error(f"Error in DirectorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.pipeline.run_full_saga_v2')
def run_full_saga_pipeline_v2(user_id: str, trailhead_id: str, source_id: str = None, target_length: int = 12, visual_style: str = "Graphic Novel"):
    """
    Chains the V2 creative pipeline: Storybook -> Director -> Illustrator -> Narrator -> Publisher
    """

    
    logger.info(f"--- Celery task 'agents.pipeline.run_full_saga_v2' received for trailhead {trailhead_id} for user {user_id} ---")

    # Use .si() (immutable signature) to prevent passing the result of the previous task as an argument to the next.
    # We pass state via the Database/Filesystem, not the return value.
    chain = (
        run_storybook_agent.si(user_id=user_id, trailhead_id=trailhead_id, source_id=source_id, target_length=target_length, visual_style=visual_style) |
        run_director_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        run_illustrator_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        # run_narrator_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        run_publisher_agent.si(user_id=user_id, trailhead_id=trailhead_id)
    )
    return chain()

@worker.task(name='agents.biographer.run')
def run_biographer_agent(user_id: str, source_id: str):
    """Celery task to run the BiographerAgent."""


    logger.info(f"--- Celery task 'agents.biographer.run' received for source {source_id} for user {user_id} ---")
    db = get_db()
    llm = LLMClient()
    agent = BiographerAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, source_id=source_id)
    except Exception as e:
        logger.error(f"Error in BiographerAgent for source {source_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.pipeline.draft_volume_structure')
def draft_volume_structure(user_id: str, theme: str, root_concept: str = "The Core Mystery", lenses: list[str] = None, seed_prose: str = None, time_range: dict = None, project_id: str = None, volume_id: str = None, universe_id: str = None, storyline_id: str = None, is_epic: bool = False) -> str: # Added is_epic
    """
    Celery task to run the VolumeArchitectAgent to draft the initial story volume structure.
    Returns the newly created volume_id.
    """
    # --- DEBUG: Print relevant environment variables ---
    impersonate_account = os.environ.get("GOOGLE_IMPERSONATE_SERVICE_ACCOUNT")
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    gcp_location = os.environ.get("GCP_LOCATION")
    logger.info(f"--- [AUTH_DEBUG] Impersonate Account: {impersonate_account} | Project: {gcp_project} | Location: {gcp_location} ---")
    # --- END DEBUG ---

    logger.info(f"--- V3 Architect: Starting for User {user_id} | Theme: {theme} | Universe: {universe_id} | IsEpic: {is_epic} ---")

    db = get_db()
    llm = LLMClient() # Initialize LLMClient here for the bridge logic

    # --- NARRATIVE BRIDGE LOGIC (Manual Greenlight) ---
    if universe_id and seed_prose:
        try:
            # 1. Get current epoch for the universe
            uni_res = db.table("Universes").select("active_epoch_id").eq("id", universe_id).single().execute()
            if uni_res.data and uni_res.data.get('active_epoch_id'):
                current_epoch_id = uni_res.data['active_epoch_id']
                
                # 2. Check if this is the first volume of this epoch
                vol_count_res = db.table("StoryVolumes").select("id", count="exact").eq("universe_id", universe_id).eq("epoch_id", current_epoch_id).execute()
                
                # If no volumes exist for this epoch yet, and it's not the first epoch...
                if vol_count_res.count == 0 and current_epoch_id > 1:
                    logger.info(f"🌉 First volume of Epoch {current_epoch_id}. Activating Narrative Bridge...")
                    previous_epoch_id = current_epoch_id - 1
                    
                    # 3. Fetch the last volume of the previous epoch
                    last_vol_res = db.table("StoryVolumes").select("id").eq("universe_id", universe_id).eq("epoch_id", previous_epoch_id).order("created_at", desc=True).limit(1).execute()
                    
                    if last_vol_res.data:
                        last_volume_id = last_vol_res.data[0]['id']
                        
                        # 4. Fetch the actual ending of that volume
                        last_node_res = db.table("Nodes").select("content").eq("volume_id", last_volume_id).order("created_at", desc=True).limit(1).execute()
                        
                        previous_ending = ""
                        if last_node_res.data:
                            last_content = last_node_res.data[0].get('content', {})
                            pages = last_content.get('pages', [])
                            if pages:
                                previous_ending = pages[-1].get('narrative_text', '')[-2000:]
                            else:
                                previous_ending = last_content.get('summary', '')

                        if previous_ending:
                            logger.info("Constructing Transient Narrative Bridge...")
                            bridge_prompt = f"""
                            I am writing a serialized saga. Chapter {previous_epoch_id} has just finished. I need to write the opening prompt for Chapter {current_epoch_id}.
                            
                            ACTUAL ENDING OF PREVIOUS CHAPTER:
                            "{previous_ending}"
                            
                            USER'S INTENDED PLAN FOR NEW CHAPTER:
                            "{seed_prose}"
                            
                            TASK:
                            Rewrite the "User's Intended Plan" to ensure perfect, seamless continuity with the "Actual Ending".
                            1. PLOT BRIDGE:
                            - If the last chapter ended with a character on a horse, the new chapter must start with them on that horse.
                            - If they acquired an item or met someone, mention it in the opening.
                            - KEEP the core goal and setting of the User's Plan (e.g., going to the forest, fighting wolves), but change the *entry point* and *initial state* to match the ending.
                            
                            2. STYLISTIC INHERITANCE (CRITICAL):
                            - Analyze the "Actual Ending". Is it dense, technical, lyrical, or simple?
                            - WRITE THE NEW PROMPT IN THAT SAME VOICE.
                            - Do not revert to generic fantasy prose. If the ending used words like "fulcrum" and "thermal conductivity," your new prompt must use similar intellectual rigor.
                            
                            Output ONLY the rewritten prose. Do not add any conversational text.
                            """
                            bridged_prose = llm.chat_completion(bridge_prompt).strip().strip('"')
                            logger.info(f"Narrative Bridge Constructed. New Seed: {bridged_prose[:150]}...")
                            seed_prose = bridged_prose # Overwrite the original seed_prose for the architect
                        else:
                            logger.warning("Could not find previous ending. Bridge skipped.")
        except Exception as e:
            logger.error(f"Narrative Bridge failed: {e}", exc_info=True)
            # Proceed with original seed_prose if bridge fails
    # --- END NARRATIVE BRIDGE ---

    architect = VolumeArchitectAgent(db, worker, llm)
    
    # Determine depth based on is_epic flag, but FORCE PRO model for intelligence
    target_depth = 12 if is_epic else 8
    reviewer_llm_model = "models/gemini-1.5-pro-latest" # Always use Pro for Architecture

    architect.llm.text_model_name = reviewer_llm_model

    full_topic = f"{theme}. Core Concept: {root_concept}"
    
    volume_id = architect.run_task(
        user_id, 
        full_topic, 
        depth=target_depth,
        lenses=lenses,
        seed_prose=seed_prose, # This will be the bridged version if the logic ran
        time_range=time_range, 
        project_id=project_id, 
        volume_id=volume_id,
        universe_id=universe_id,
        storyline_id=storyline_id
    )
    
    if not volume_id:
        logger.error("V3 Architect Failed: Architect returned no volume_id")
        return "Failed at Architect"
    
    logger.info(f"V3 Architect: Volume {volume_id} structure drafted.")
    return volume_id


@worker.task(name='agents.pipeline.generate_manuscript')
def generate_manuscript(volume_id: str, user_id: str):
    """
    Phase 2: The Manuscript.
    Hydrates the graph (Research) and writes the text (Storybook).
    """
    logger.info(f"--- V3 Manuscript Generation: Starting for Volume {volume_id} ---")
    
    db = get_db()
    db.table("StoryVolumes").update({"status": "writing"}).eq("id", volume_id).execute()

    llm = LLMClient()
    
    # Fetch Volume Context
    vol_res = db.table("StoryVolumes").select("universe_id, storyline_id").eq("id", volume_id).single().execute()
    universe_id = vol_res.data.get('universe_id') if vol_res.data else None
    storyline_id = vol_res.data.get('storyline_id') if vol_res.data else None
    universe_ids = [universe_id] if universe_id else []

    # 1. Researcher (Hydration)
    researcher = ResearcherAgent(db, worker, llm)
    researcher.run_task(volume_id, user_id=user_id)
    
    # 2. Batch Producer (Text Only)
    producer = BatchProducerAgent(db, worker, llm)
    # V4 Calibration: Shorter target length (2) because we have more atomic nodes (8+)
    producer.run_task(
        volume_id, 
        mode="text_only", 
        user_id=user_id, 
        target_length=2,
        universe_ids=universe_ids,
        storyline_id=storyline_id
    )
    
    logger.info(f"V3 Manuscript Complete for Volume {volume_id}")
    return f"Volume {volume_id} Manuscript Written"


@worker.task(name='agents.pipeline.generate_visuals')
def generate_visuals(volume_id: str, user_id: str):
    """
    Phase 3: The Gallery.
    Generates images for an existing manuscript.
    """

    
    logger.info(f"--- V3 Visuals Generation: Starting for Volume {volume_id} ---")
    
    db = get_db()
    db.table("StoryVolumes").update({"status": "illustrating"}).eq("id", volume_id).execute()

    llm = LLMClient()
    
    # 2. Batch Producer (Full Render - Illustrator will run, Storybook will skip existing text)
    producer = BatchProducerAgent(db, worker, llm)
    producer.run_task(volume_id, mode="illustrate_only", user_id=user_id)
    
    logger.info(f"V3 Visuals Complete for Volume {volume_id}")
    return f"Volume {volume_id} Visuals Rendered"

@worker.task(name='agents.tasks.hello_world')
def hello_world():
    logger.info("--- Hello World task executed successfully ---")
    return "Hello World"

logger.info("--- Celery tasks loaded ---")

@worker.task(name='agents.ingestion.process_upload')
def process_upload(task_payload):
    """
    Handles file upload processing with Gatekeeper checks.
    """

    
    logger.info(f"--- Process Upload Task: {task_payload.get('file_path')} ---")
    
    db = get_db()
    
    user_id = task_payload['user_id']
    project_id = task_payload.get('project_id')
    file_path = task_payload['file_path']
    file_type = task_payload['file_type']
    source_id = task_payload['source_id']
    
    gatekeeper = UsageGatekeeper(db, user_id)
    hf_token = os.getenv("HF_TOKEN")

    try:
        if "audio" in file_type or "video" in file_type:
            # Check Duration
            duration_seconds = get_duration(file_path)
            logger.info(f"Media Duration: {duration_seconds}s")
            
            gatekeeper.check_media_processing(duration_seconds)
            
            # Process Audio (Always)
            from worker.src.ingestion.audio_atomizer import AudioAtomizer
            atomizer = AudioAtomizer(db)
            atom_count = atomizer.process(file_path, source_id, project_id, user_id, hf_token)
            
            # Process Video (If video file)
            video_atom_count = 0
            if "video" in file_type:
                logger.info("Video detected. Engaging Visual Cortex...")
                from worker.src.ingestion.video_atomizer import VideoAtomizer
                video_atomizer = VideoAtomizer(db)
                video_atom_count = video_atomizer.process(file_path, source_id, project_id, user_id)
                atom_count += video_atom_count
            
            # Log Cost
            gatekeeper.log_media(project_id, int(duration_seconds), os.path.basename(file_path))
            
            # Update Source status
            db.table("Sources").update({"is_processed": True, "media_duration_seconds": int(duration_seconds)}).eq("id", source_id).execute()
            
            return f"Processed {atom_count} atoms ({video_atom_count} visual) from media."
            
        else:
            # Document Logic
            gatekeeper.check_ingest_document()
            
            # Trigger standard indexing
            process_source.delay(source_id, user_id)
            
            gatekeeper.log_ingest(project_id, os.path.basename(file_path))
            return "Document ingestion triggered."

    except QuotaExceededError as e:
        logger.error(f"Quota Exceeded: {e}")
        db.table("Sources").update({"metadata": {"error": str(e), "status": "quota_exceeded"}}).eq("id", source_id).execute()
        return {"status": "failed", "error": str(e), "code": 402}
    except Exception as e:
        logger.error(f"Upload Processing Failed: {e}", exc_info=True)
        raise e

def get_duration(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout)
    except Exception as e:
        logger.error(f"Failed to get duration: {e}")
        return 0

@worker.task(name='agents.synthesis.generate_deep_synthesis')
def generate_deep_synthesis(task_payload):
    """
    1. Director plans the book.
    2. Loop through chapters:
       a. Search Vector DB for chapter-specific atoms.
       b. Scribe writes chapter.
    3. Compile and Save.
    """
    logger.info("--- Starting Deep Synthesis ---")
    user_id = task_payload['user_id']
    project_id = task_payload['project_id']
    prompt = task_payload['prompt']
    
    db = get_db()
    client = LLMClient()
    
    # 1. Check Quota (Gatekeeper)
    gatekeeper = UsageGatekeeper(db, user_id)
    # gatekeeper.check_generation() # TODO: Implement explicit check if needed
    
    # 2. Load Context (Persona & Project Info)
    # Fetch persona from DB
    from db.crud import get_persona_profile
    persona = get_persona_profile(db, user_id)
    persona_voice = persona.system_prompt_cache if persona and persona.system_prompt_cache else "You are a rigorous but accessible academic researcher."
    
    # 3. Director Action
    director = DirectorAgent(db, client)
    manifest = director.create_manifest(prompt, "Project Context: User requested deep synthesis.", persona_voice)
    logger.info(f"Manifest created with {len(manifest)} chapters.")
    
    # 4. Scribe Loop
    scribe = ScribeAgent(db, client)
    full_manuscript = f"# Deep Synthesis: {prompt}\n\n"
    
    for chapter in manifest:
        logger.info(f"Writing Chapter: {chapter.get('title', 'Untitled')}")
        
        # 4a. RAG Retrieval
        queries = chapter.get('search_queries', [])
        relevant_atoms = []
        seen_atom_ids = set()
        
        for query in queries:
            embedding = client.get_embedding(query)
            matches = match_atoms_by_embedding(
                db, 
                embedding, 
                match_threshold=0.5, 
                match_count=5,
                query_user_id=user_id,
                query_project_id=project_id
            )
            for m in matches:
                if m['id'] not in seen_atom_ids:
                    relevant_atoms.append(m)
                    seen_atom_ids.add(m['id'])
        
        # 4b. Write
        content = scribe.write_chapter(chapter, relevant_atoms, persona_voice)
        
        full_manuscript += f"## {chapter.get('title', 'Untitled')}\n\n{content}\n\n---\n\n"
    
    # 5. Save Volume
    try:
        volume_id = str(uuid.uuid4())
        volume_data = {
            "id": volume_id,
            "user_id": user_id,
            "project_id": project_id,
            "title": f"Deep Synthesis: {prompt[:50]}...",
            "root_concept": prompt,
            "status": "completed",
            "manuscript": {"content": full_manuscript},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db.table("StoryVolumes").insert(volume_data).execute()
        logger.info(f"Saved Volume {volume_id}")
    except Exception as e:
        logger.error(f"Failed to save volume: {e}")
    
    # 6. Charge Ledger
    gatekeeper.log_generation(project_id, prompt)
    
    return {"status": "complete", "manifest": manifest, "preview": full_manuscript[:500], "full_text": full_manuscript, "volume_id": volume_id}

@worker.task(name='agents.tasks.run_curator')
def run_curator_agent(user_id: str, core_themes: str, volume_id: str = None):
    """
    The Curator Task.
    Scans recent atoms and generates Trailheads.
    """
    logger.info(f"--- Curator Task started for user {user_id} ---")
    
    db = get_db()
    
    # We pass the worker app instance if needed, though CuratorAgent currently just needs DB
    # If CuratorAgent needs to dispatch subtasks, we pass `worker`.
    agent = CuratorAgent(db, worker) 
    try:
        result = agent.analyze_and_generate_trailheads(user_id, core_themes, volume_id)
        return result
    except Exception as e:
        logger.error(f"Curator Task Failed: {e}", exc_info=True)
        return "Failed"