import os
import uuid
import logging
import json
from typing import Any, List, Optional, Dict
from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv
import uvicorn
from celery.result import AsyncResult

# Load environment variables
load_dotenv()

# Sentry Initialization
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Import Schemas from DB
from db import schemas
from db.schemas import (
    NodeCreate, NodeUpdate, EdgeCreate, BranchCreate, BranchUpdate, 
    SourceType, CreateNodeRequest, ExpandNodeRequest,
    UniverseUpdate, Epoch, EpochCreate, EpochUpdate
)

# Import CRUD functions
from db.crud import (
    create_node, update_node, delete_node, get_node, 
    create_edge, delete_edge, 
    get_branches_for_volume, create_branch, update_branch,
    create_category, get_category, get_all_categories_for_user, update_category, delete_category,
    get_all_sources_for_user, get_all_sources_with_series_info_for_user,
    get_trailheads_for_user, get_lenses_for_user, get_user_id_by_email,
    create_universe, get_all_universes_for_user, get_universe, update_universe,
    create_storyline, get_all_storylines_for_universe,
    get_epochs_for_universe, create_epoch, update_epoch, 
    get_latent_atom_count, get_all_atoms_for_universe, patch_atom_discovery_epoch,
    get_persona_profile
)
from worker.src.archetypes import get_all_archetypes
from worker.src.services.context_engine import ContextEngine

# Import Tasks
from worker.src.agents.tasks import (
    scan_and_process_source, run_writers_room, finalize_volume, 
    draft_volume_structure, generate_manuscript, generate_visuals,
    worker as worker_app
)
from worker.src.agents.architect_v2 import VolumeArchitectAgent
from worker.src.agents.concept_agent import ConceptAgent
from llm.client import get_llm_client
from services.billing.gatekeeper import UsageGatekeeper, QuotaExceededError
from services.billing.api import router as billing_router
from auth.dependencies import get_supabase, get_current_user

# --- 1. REQUEST MODELS (Defined early to prevent NameErrors) ---

class GenerateVolumeRequest(BaseModel):
    topic: str
    seed_prose: Optional[str] = None
    depth: int = 6
    lenses: Optional[List[str]] = []
    time_range: Optional[Dict] = None
    project_id: Optional[str] = None
    universe_id: Optional[str] = None
    storyline_id: Optional[str] = None
    is_epic: Optional[bool] = False

class FleshOutConceptRequest(BaseModel):
    prompt: str

class UnlockAtomRequest(BaseModel):
    discovery_epoch_id: int

class InitializeProductionRequest(BaseModel):
    trailhead: Dict
    universe_id: Optional[str] = None
    storyline_id: Optional[str] = None

# --- 2. CONFIGURATION & APP INIT ---

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

llm_service = get_llm_client()
app = FastAPI(title="Sunroom API")

if SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)

app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000", "https://sunroom-de.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_supabase_admin() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- 3. INGESTION ENDPOINTS ---

@app.post("/api/v1/sources", status_code=202)
async def ingest_source(
    user: Any = Depends(get_current_user), 
    db: Client = Depends(get_supabase_admin),
    file: UploadFile = File(...),
    category_id: Optional[str] = Form(None),
    manual_lens_name: Optional[str] = Form(None),
    universe_id: Optional[str] = Form(None),
    discovery_epoch_id: Optional[int] = Form(None)
):
    gatekeeper = UsageGatekeeper(db, user.id)
    try:
        gatekeeper.check_ingest_document()
    except QuotaExceededError as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        storage_path = f"{user.id}/{uuid.uuid4()}_{file.filename}"
        file_content = await file.read()
        await run_in_threadpool(db.storage.from_("sources").upload, path=storage_path, file=file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload: {e}")

    is_audio = file.content_type and file.content_type.startswith('audio/')
    status = 'processing' if is_audio else 'completed'

    metadata = {}
    if manual_lens_name: metadata["manual_lens_name"] = manual_lens_name
    if universe_id: metadata["universe_id"] = universe_id
    if discovery_epoch_id is not None: metadata["discovery_epoch_id"] = discovery_epoch_id

    insert_data = {
        "user_id": user.id,
        "title": file.filename,
        "storage_path": storage_path, 
        "metadata": metadata,
        "source_type": SourceType.UPLOADED_AUDIO if is_audio else SourceType.UPLOADED_TEXT,
        "category_id": category_id,
        "processing_status": status
    }
    
    res = db.table("Sources").insert(insert_data).execute()
    new_source = res.data[0]
    
    if status == 'processing' or not is_audio:
        scan_and_process_source.delay(source_id=new_source['id'], user_id=user.id)
    
    gatekeeper.log_ingest(project_id=None, file_name=file.filename)
    return {"message": "Ingestion started", "source_id": new_source['id']}

@app.get("/api/v1/sources")
async def get_sources(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_all_sources_with_series_info_for_user(db, user.id)

@app.delete("/api/v1/sources/{source_id}")
async def delete_source(source_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    res = db.table("Sources").select("id, user_id, storage_path").eq("id", source_id).single().execute()
    if not res.data: raise HTTPException(status_code=404)
    if res.data['storage_path']:
        try: await run_in_threadpool(db.storage.from_("sources").remove, paths=[res.data['storage_path']])
        except Exception: pass
    db.table("Sources").delete().eq("id", source_id).execute()
    return {"message": "Deleted"}

# --- 4. MULTIVERSE & ONTOLOGY ENDPOINTS ---

@app.get("/api/v1/archetypes")
async def get_archetypes_endpoint():
    return get_all_archetypes()

@app.get("/api/v1/universes", response_model=List[schemas.Universe])
async def get_universes(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_all_universes_for_user(db, user.id)

@app.post("/api/v1/universes", response_model=schemas.Universe, status_code=201)
async def create_universe_route(universe: schemas.UniverseCreate, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return create_universe(db, universe, user.id)

@app.get("/api/v1/universes/{universe_id}", response_model=schemas.Universe)
async def get_uni(universe_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    u = get_universe(db, universe_id, user.id)
    if not u: raise HTTPException(status_code=404)
    return u

@app.patch("/api/v1/universes/{universe_id}", response_model=schemas.Universe)
async def update_uni(universe_id: str, universe: schemas.UniverseUpdate, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return update_universe(db, universe_id, universe, user.id)

@app.get("/api/v1/universes/{universe_id}/storylines", response_model=List[schemas.Storyline])
async def get_storylines(universe_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    if not get_universe(db, universe_id, user.id): raise HTTPException(status_code=404)
    return get_all_storylines_for_universe(db, universe_id, user.id)

@app.get("/api/v1/universes/{universe_id}/epochs", response_model=List[schemas.Epoch])
async def get_epochs_endpoint(universe_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_epochs_for_universe(db, universe_id, user.id)

@app.post("/api/v1/universes/{universe_id}/epochs", status_code=201)
async def create_ep(universe_id: str, epoch: schemas.EpochCreate, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return create_epoch(db, epoch, universe_id, user.id)

@app.patch("/api/v1/epochs/{epoch_id}", response_model=schemas.Epoch)
async def update_ep(epoch_id: int, epoch: schemas.EpochUpdate, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return update_epoch(db, epoch_id, epoch, user.id)

@app.get("/api/v1/universes/{universe_id}/latent-knowledge")
async def get_latent(universe_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    count = get_latent_atom_count(db, universe_id, user.id)
    return {"universe_id": universe_id, "latent_atom_count": count}

@app.get("/api/v1/universes/{universe_id}/atoms", response_model=List[schemas.Atom])
async def get_uni_atoms(universe_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_all_atoms_for_universe(db, universe_id, user.id)

@app.patch("/api/v1/atoms/{atom_id}/unlock")
async def unlock_at(atom_id: str, req: UnlockAtomRequest, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return patch_atom_discovery_epoch(db, atom_id, req.discovery_epoch_id, user.id)

@app.get("/api/v1/storylines/dashboard")
async def get_storylines_dashboard(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    """
    Returns a hierarchical view: Storylines -> Volumes.
    Used for the new Omnibus Dashboard.
    """
    # 1. Fetch Storylines
    sl_res = db.table("Storylines").select("*").eq("user_id", user.id).order("updated_at", desc=True).execute()
    storylines = sl_res.data
    
    # 2. Enrich with Volumes
    result = []
    for sl in storylines:
        vol_res = db.table("StoryVolumes").select("id, title, status, created_at, universe_id").eq("storyline_id", sl['id']).order("created_at").execute()
        sl['volumes'] = vol_res.data
        result.append(sl)
        
    return result

@app.get("/api/v1/storylines/{storyline_id}")
async def get_storyline_detail(storyline_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    """
    Returns full details for a single Storyline, including its volumes.
    """
    # 1. Fetch Storyline
    sl_res = db.table("Storylines").select("*").eq("id", storyline_id).eq("user_id", user.id).single().execute()
    storyline = sl_res.data
    if not storyline: raise HTTPException(status_code=404, detail="Storyline not found")
    
    # 2. Fetch Volumes (Ordered by creation, which proxies for Epoch order)
    vol_res = db.table("StoryVolumes").select("*").eq("storyline_id", storyline_id).order("created_at").execute()
    storyline['volumes'] = vol_res.data
    
    # 3. Fetch Universe Name (Convenience)
    if storyline.get('universe_id'):
        uni_res = db.table("Universes").select("name").eq("id", storyline['universe_id']).single().execute()
        storyline['universe_name'] = uni_res.data.get('name') if uni_res.data else "Unknown Universe"
        
    return storyline

# --- 5. VOLUMES & GENERATION ENDPOINTS ---

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str, user: Any = Depends(get_current_user)):
    """
    Check the status of a background Celery task.
    """
    task_result = AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None
    }
    if task_result.status == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.status == 'FAILURE':
        response["result"] = str(task_result.result)
    return response

@app.get("/api/v1/volumes")
async def get_vols(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    res = db.table("StoryVolumes").select("*").eq("user_id", user.id).order("created_at", desc=True).execute()
    return res.data

@app.post("/api/v1/volumes/generate")
async def generate_volume_route(request: GenerateVolumeRequest, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    gatekeeper = UsageGatekeeper(db, user.id)
    try: gatekeeper.check_generation()
    except QuotaExceededError as e: raise HTTPException(status_code=403, detail=str(e))

    # --- TITLE & ROOT CONCEPT RESOLUTION ---
    final_volume_title = request.topic # Default to request topic
    final_root_concept = request.seed_prose or request.topic # Default root concept is seed_prose
    epoch_name_for_theme = request.topic # Default theme for architect

    if request.universe_id:
        try:
            uni_res = db.table("Universes").select("active_epoch_id").eq("id", request.universe_id).single().execute()
            if uni_res.data and uni_res.data.get('active_epoch_id'):
                active_epoch_id = uni_res.data['active_epoch_id']
                epoch_res = db.table("Epochs").select("name").eq("id", active_epoch_id).single().execute()
                if epoch_res.data and epoch_res.data.get('name'):
                    current_epoch_name = epoch_res.data['name']
                    
                    # Calculate Relative Epoch Number (Count epochs <= active_epoch_id)
                    count_res = db.table("Epochs").select("id", count="exact").eq("universe_id", request.universe_id).lte("id", active_epoch_id).execute()
                    relative_epoch_number = count_res.count
                    
                    # Check if the epoch name already contains the epoch number to avoid duplication
                    if current_epoch_name.strip().lower().startswith(f"epoch {relative_epoch_number}"):
                        final_volume_title = current_epoch_name
                    else:
                        final_volume_title = f"Epoch {relative_epoch_number}: {current_epoch_name}" # Explicit, clean title
                    
                    epoch_name_for_theme = current_epoch_name # Use concise name for architect's theme
        except Exception as e:
            logging.error(f"Failed to resolve Epoch Name for title: {e}")

    vol_data = {
        "user_id": user.id, 
        "title": final_volume_title, 
        "root_concept": final_root_concept, # Use the actual seed prose as the rich root concept
        "status": "architecting", 
        "universe_id": request.universe_id,
        "storyline_id": request.storyline_id, 
        "is_epic": request.is_epic,
        "epoch_id": active_epoch_id if request.universe_id and 'active_epoch_id' in locals() else None # Store epoch_id
    }
    res = db.table("StoryVolumes").insert(vol_data).execute()
    new_vol = res.data[0]
    
    # CAPTURE THE TASK ID
    task = draft_volume_structure.delay(
        volume_id=new_vol['id'], user_id=user.id, theme=epoch_name_for_theme, # Pass clean epoch name as theme
        seed_prose=request.seed_prose, # Pass the detailed seed prose
        root_concept=final_root_concept, # Pass the detailed seed prose as root concept
        lenses=request.lenses,
        time_range=request.time_range, project_id=request.project_id,
        universe_id=request.universe_id, storyline_id=request.storyline_id,
        is_epic=request.is_epic
    )
    
    gatekeeper.log_generation(project_id=request.project_id, volume_title=final_volume_title)
    
    # RETURN TASK ID SO FRONTEND CAN POLL
    return {"volume_id": new_vol['id'], "task_id": task.id}

@app.post("/api/v1/volumes/flesh-out-concept")
async def flesh_out_route(request: FleshOutConceptRequest, user: Any = Depends(get_current_user)):
    agent = ConceptAgent(db=None, worker=None, llm=llm_service)
    brief = await run_in_threadpool(agent.run_task, user_prompt=request.prompt)
    return brief

@app.post("/api/v1/volumes/{volume_id}/write")
async def write_vol(volume_id: str, user: Any = Depends(get_current_user)):
    generate_manuscript.delay(volume_id=volume_id, user_id=user.id)
    return {"message": "Started"}

@app.post("/api/v1/volumes/{volume_id}/illustrate")
async def illu_vol(volume_id: str, user: Any = Depends(get_current_user)):
    generate_visuals.delay(volume_id=volume_id, user_id=user.id)
    return {"message": "Started"}

@app.post("/api/v1/volumes/{volume_id}/advance_epoch")
async def advance_epoch_route(volume_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    """
    Finalizes a volume's text, crystallizes its memory, and advances the Universe's active_epoch_id.
    This is the first step in the manual, user-driven epoch transition.
    """
    # Verify the volume belongs to the user for security
    res = db.table("StoryVolumes").select("id, user_id").eq("id", volume_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Volume not found")
    if res.data['user_id'] != user.id:
        raise HTTPException(status_code=403, detail="User not authorized to advance this volume")

    task = finalize_volume.delay(volume_id=volume_id)
    return {"message": "Epoch advancement process started.", "task_id": task.id}

@app.post("/api/v1/production/initialize")
async def initialize_production_route(request: InitializeProductionRequest, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    """
    Triggers the V7 Writers' Room (Full Script Production).
    Creates a temporary volume to track the subgraph/script.
    """
    gatekeeper = UsageGatekeeper(db, user.id)
    try: gatekeeper.check_generation()
    except QuotaExceededError as e: raise HTTPException(status_code=403, detail=str(e))

    # 1. Create a StoryVolume for this production run
    vol_data = {
        "user_id": user.id,
        "title": request.trailhead.get('title', 'Project Production'),
        "root_concept": request.trailhead.get('premise', ''),
        "status": "production_started",
        "universe_id": request.universe_id,
        "storyline_id": request.storyline_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    res = db.table("StoryVolumes").insert(vol_data).execute()
    new_vol = res.data[0]

    # 2. Trigger the Writers' Room task
    task = run_writers_room.delay(
        trailhead=request.trailhead,
        volume_id=new_vol['id'],
        user_id=user.id
    )

    gatekeeper.log_generation(project_id=None, volume_title=vol_data['title'])

    return {
        "volume_id": new_vol['id'],
        "task_id": task.id,
        "message": "Writers' Room Initialized"
    }
    
@app.delete("/api/v1/volumes/{volume_id}", status_code=200)
async def delete_volume_route(volume_id: str, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    """
    Deletes a volume and its associated data.
    """
    try:
        # First, verify the volume belongs to the user
        res = db.table("StoryVolumes").select("id, user_id").eq("id", volume_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Volume not found")
        if res.data['user_id'] != user.id:
            raise HTTPException(status_code=403, detail="User not authorized to delete this volume")

        # Now, delete the volume and its atoms
        from db.crud import delete_volume
        delete_volume(db, volume_id)
        
        return {"message": "Volume deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting volume {volume_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while deleting volume")

# --- 6. CATEGORIES & TRAILHEADS ---

@app.post("/api/v1/categories")
async def create_cat_route(category: schemas.CategoryCreate, user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return create_category(db, category, user.id)

@app.get("/api/v1/categories")
async def get_cats_route(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_all_categories_for_user(db, user.id)

@app.get("/api/v1/trailheads")
async def get_trails(user: Any = Depends(get_current_user), db: Client = Depends(get_supabase_admin)):
    return get_trailheads_for_user(db, user.id)

# --- 7. GRAPH ENGINE (Nodes, Edges, Materialize) ---

@app.get("/api/v1/volumes/{volume_id}/nodes")
async def get_nodes(volume_id: str, db: Client = Depends(get_supabase_admin)):
    res = db.table("Nodes").select("*").eq("volume_id", volume_id).execute()
    return res.data

@app.get("/api/v1/volumes/{volume_id}/debug_nodes")
async def debug_get_nodes_for_volume(volume_id: str, db: Client = Depends(get_supabase_admin)):
    """A temporary debug endpoint to fetch raw node data."""
    res = db.table("Nodes").select("*").eq("volume_id", volume_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No nodes found for this volume.")
    return res.data

@app.patch("/api/v1/nodes/{node_id}")
async def up_node(node_id: str, node: NodeUpdate, db: Client = Depends(get_supabase_admin)):
    return update_node(db, node_id, node)

@app.get("/api/v1/nodes/{node_id}/context")
async def get_node_ctx(node_id: str, db: Client = Depends(get_supabase_admin)):
    node = get_node(db, node_id)
    context_engine = ContextEngine(db)
    return {"context": context_engine.get_context_from_db(node['volume_id'], node_id)}

@app.post("/api/v1/nodes/expand")
async def exp_node(request: ExpandNodeRequest, db: Client = Depends(get_supabase_admin)):
    architect = VolumeArchitectAgent(db, worker_app, llm_service)
    return {"options": architect.expand_node_task(request.volume_id, request.node_id, request.branch_id)}

@app.post("/api/v1/nodes")
async def materialize_node(request: CreateNodeRequest, db: Client = Depends(get_supabase_admin)):
    new_id = str(uuid.uuid4())
    node_data = {
        "id": new_id, "volume_id": request.volume_id, "branch_id": request.branch_id,
        "parent_node_id": request.parent_node_id, "type": request.type,
        "content": {"title": request.title, "summary": request.summary, "status": "draft"}
    }
    db.table("Nodes").insert(node_data).execute()
    edge_data = {
        "volume_id": request.volume_id, "source_node_id": request.parent_node_id,
        "target_node_id": new_id, "type": request.relationship_type, "weight": 1.0
    }
    db.table("Edges").insert(edge_data).execute()
    return {"id": new_id, "status": "materialized"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)