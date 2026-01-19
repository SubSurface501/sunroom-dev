from typing import List, Optional
import logging
import uuid
from datetime import datetime, timezone
from supabase import Client
from db import schemas

# Configure logging
logger = logging.getLogger(__name__)

# --- 1. CORE GRAPH CRUD ---

def create_node(db: Client, node: schemas.NodeCreate) -> schemas.Node:
    data = node.model_dump()
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    # Ensure datetimes are ISO strings for JSON serialization
    if data.get('created_at') and isinstance(data['created_at'], datetime):
        data['created_at'] = data['created_at'].isoformat()
    elif not data.get('created_at'):
        data['created_at'] = datetime.now(timezone.utc).isoformat()

    if data.get('updated_at') and isinstance(data['updated_at'], datetime):
        data['updated_at'] = data['updated_at'].isoformat()
    elif not data.get('updated_at'):
        data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
    res = db.table("Nodes").insert(data).execute()
    return schemas.Node(**res.data[0])

def update_node(db: Client, node_id: str, node: schemas.NodeUpdate) -> Optional[schemas.Node]:
    update_data = node.model_dump(exclude_unset=True)
    res = db.table("Nodes").update(update_data).eq("id", node_id).execute()
    return schemas.Node(**res.data[0]) if res.data else None

def get_node(db: Client, node_id: str) -> Optional[schemas.Node]:
    try:
        res = db.table("Nodes").select("*").eq("id", node_id).single().execute()
        return schemas.Node(**res.data) if res.data else None
    except Exception as e:
        logger.error(f"Error fetching node {node_id}: {e}")
        return None

def delete_node(db: Client, node_id: str):
    return db.table("Nodes").delete().eq("id", node_id).execute()

def create_edge(db: Client, edge: schemas.EdgeCreate) -> schemas.Edge:
    data = edge.model_dump()
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    if data.get('created_at') and isinstance(data['created_at'], datetime):
        data['created_at'] = data['created_at'].isoformat()
    elif not data.get('created_at'):
        data['created_at'] = datetime.now(timezone.utc).isoformat()
    res = db.table("Edges").insert(data).execute()
    return schemas.Edge(**res.data[0])

def delete_edge(db: Client, edge_id: str):
    return db.table("Edges").delete().eq("id", edge_id).execute()

def get_branches_for_volume(db: Client, volume_id: str) -> List[schemas.Branch]:
    res = db.table("Branches").select("*").eq("volume_id", volume_id).execute()
    return [schemas.Branch(**b) for b in res.data]


def create_branch(db: Client, branch: schemas.BranchCreate) -> schemas.Branch:
    data = branch.model_dump()
    if not data.get('id'):
        data['id'] = str(uuid.uuid4())
    if data.get('created_at') and isinstance(data['created_at'], datetime):
        data['created_at'] = data['created_at'].isoformat()
    elif not data.get('created_at'):
        data['created_at'] = datetime.now(timezone.utc).isoformat()
    res = db.table("Branches").insert(data).execute()
    return schemas.Branch(**res.data[0])

def update_branch(db: Client, branch_id: str, branch: schemas.BranchUpdate) -> Optional[schemas.Branch]:
    update_data = branch.model_dump(exclude_unset=True)
    res = db.table("Branches").update(update_data).eq("id", branch_id).execute()
    return schemas.Branch(**res.data[0]) if res.data else None

# --- 2. CATEGORY, SOURCE & PERSONA CRUD ---

def create_category(db: Client, category: schemas.CategoryCreate, user_id: str) -> schemas.Category:
    data = category.model_dump()
    data['user_id'] = user_id
    res = db.table("Categories").insert(data).execute()
    return schemas.Category(**res.data[0])

def get_category(db: Client, category_id: str, user_id: str) -> Optional[schemas.Category]:
    res = db.table("Categories").select("*").eq("id", category_id).eq("user_id", user_id).single().execute()
    return schemas.Category(**res.data) if res.data else None

def get_all_categories_for_user(db: Client, user_id: str) -> List[schemas.Category]:
    res = db.table("Categories").select("*").eq("user_id", user_id).execute()
    return [schemas.Category(**c) for c in res.data]

def update_category(db: Client, category_id: str, category: schemas.CategoryUpdate, user_id: str) -> Optional[schemas.Category]:
    update_data = category.model_dump(exclude_unset=True)
    res = db.table("Categories").update(update_data).eq("id", category_id).eq("user_id", user_id).execute()
    return schemas.Category(**res.data[0]) if res.data else None

def delete_category(db: Client, category_id: str, user_id: str):
    return db.table("Categories").delete().eq("id", category_id).eq("user_id", user_id).execute()

def get_all_sources_for_user(db: Client, user_id: str):
    return db.table("Sources").select("*").eq("user_id", user_id).execute().data

def get_all_sources_with_series_info_for_user(db: Client, user_id: str):
    """Retrieves all sources for the user without complex joins."""
    try:
        res = db.table("Sources").select("*").eq("user_id", user_id).execute()
        return res.data
    except Exception as e:
        logger.error(f"Error fetching sources: {e}")
        return []

def get_trailheads_for_user(db: Client, user_id: str):
    return db.table("Trailheads").select("*").eq("user_id", user_id).execute().data

def get_lenses_for_user(db: Client, user_id: str):
    res = db.table("Atoms").select("metadata->>cluster_name").eq("user_id", user_id).execute()
    lenses = list(set([r['cluster_name'] for r in res.data if r.get('cluster_name')]))
    return [{"name": lens} for lens in lenses]

def get_persona_profile(db: Client, user_id: str) -> Optional[dict]:
    """REQUIRED BY REVIEWER: Retrieves the user's main persona profile."""
    try:
        # Use .limit(1).execute() instead of .single().execute() to avoid 406 on empty/multiple results
        res = db.table("persona_profiles").select("*").eq("user_id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.warning(f"No persona profile found for user {user_id}: {e}")
        return None

# --- 3. VECTOR SEARCH & ATOM RETRIEVAL ---

def match_atoms_by_embedding(
    db: Client, 
    query_embedding: List[float], 
    match_threshold: float, 
    match_count: int, 
    query_user_id: str = None,
    query_project_id: str = None,
    filter_lenses: List[str] = None,
    filter_universe_ids: List[str] = None,
    filter_permanence_types: List[str] = None,
    filter_storyline_id: str = None,
    filter_epoch_id: int = None,
    filter_start_date: str = None,
    filter_end_date: str = None
) -> List[dict]:
    params = {
        "query_embedding": query_embedding,
        "match_threshold": match_threshold,
        "match_count": match_count,
        "query_user_id": query_user_id,
        "query_project_id": query_project_id,
        "filter_lenses": filter_lenses,
        "filter_universe_ids": filter_universe_ids,
        "filter_permanence_types": filter_permanence_types,
        "filter_start_date": filter_start_date,
        "filter_end_date": filter_end_date,
        "filter_storyline_id": filter_storyline_id,
        "query_epoch_id": filter_epoch_id
    }
    try:
        res = db.rpc("match_atoms", params).execute()
        return res.data
    except Exception as e:
        logger.error(f"Error calling match_atoms RPC: {e}")
        return []

def get_user_id_by_email(db: Client, email: str) -> Optional[str]:
    try:
        res = db.rpc("get_user_id_by_email", {"p_email": email}).execute()
        return res.data if res.data else None
    except Exception as e:
        logger.error(f"Error calling get_user_id_by_email RPC: {e}")
        return None

# --- 4. UNIVERSE, STORYLINE & EPOCH CRUD ---

def create_universe(db: Client, universe: schemas.UniverseCreate, user_id: str) -> schemas.Universe:
    from llm.client import get_llm_client
    import json

    data = universe.model_dump()
    data['user_id'] = user_id

    # --- Genesis Agent (Bible Creator) ---
    world_bible = {}
    if universe.description:
        llm = get_llm_client()
        prompt = f"""
        Analyze the following seed prose to establish a "World Bible" of immutable facts.
        Extract key entities and their properties.
        
        Rules:
        - Identify the protagonist. Extract their name, any aliases, and create a list of plausible but incorrect names (e.g., common fantasy names of the same gender) under "forbidden_names".
        - Identify the primary setting and any core laws or principles.
        - Return ONLY a JSON object in the format {{"entities": {{"protagonist": {{...}}, "setting": {{...}}}}}}.
        
        Prose:
        ---
        {universe.description[:4000]}
        ---

        JSON Output:
        """
        try:
            response = llm.chat_completion(prompt)
            cleaned_response = response.strip().replace('`', '').replace('json', '')
            world_bible = json.loads(cleaned_response)
        except Exception as e:
            logger.error(f"Genesis Agent failed to extract World Bible: {e}")
            # Fallback to a simple structure if LLM fails
            world_bible = {"initial_description": universe.description}

    data['world_bible'] = world_bible
    # --- End Genesis Agent ---

    res = db.table("Universes").insert(data).execute()
    new_universe = schemas.Universe(**res.data[0])
    
    # Auto-create default storyline
    try:
        db.table("Storylines").insert({
            "universe_id": new_universe.id,
            "name": "Main Storyline",
            "user_id": user_id
        }).execute()
    except Exception as e:
        logger.error(f"Failed to auto-create default storyline for universe {new_universe.id}: {e}")
        
    return new_universe

def get_all_universes_for_user(db: Client, user_id: str) -> List[schemas.Universe]:
    res = db.table("Universes").select("*").eq("user_id", user_id).order("name").execute()
    return [schemas.Universe(**u) for u in res.data]

def get_universe(db: Client, universe_id: str, user_id: str) -> Optional[schemas.Universe]:
    try:
        res = db.table("Universes").select("*").eq("id", universe_id).eq("user_id", user_id).single().execute()
        return schemas.Universe(**res.data) if res.data else None
    except Exception: return None

def update_universe(db: Client, universe_id: str, universe: schemas.UniverseUpdate, user_id: str) -> Optional[schemas.Universe]:
    update_data = universe.model_dump(exclude_unset=True)
    res = db.table("Universes").update(update_data).eq("id", universe_id).eq("user_id", user_id).execute()
    return schemas.Universe(**res.data[0]) if res.data else None

def create_storyline(db: Client, storyline: schemas.StorylineCreate, user_id: str) -> schemas.Storyline:
    data = storyline.model_dump()
    data['user_id'] = user_id
    res = db.table("Storylines").insert(data).execute()
    return schemas.Storyline(**res.data[0])

def get_all_storylines_for_universe(db: Client, universe_id: str, user_id: str) -> List[schemas.Storyline]:
    res = db.table("Storylines").select("*").eq("universe_id", universe_id).eq("user_id", user_id).execute()
    return [schemas.Storyline(**s) for s in res.data]

def get_epochs_for_universe(db: Client, universe_id: str, user_id: str) -> List[schemas.Epoch]:
    res = db.table("Epochs").select("*").eq("universe_id", universe_id).order("id").execute()
    # Hotfix for Supabase returning '[]' for empty jsonb, which fails Pydantic validation for Dict fields.
    for e in res.data:
        if isinstance(e.get('narrative_ledger'), list):
            e['narrative_ledger'] = {}
    return [schemas.Epoch(**e) for e in res.data]

def create_epoch(db: Client, epoch_data: schemas.EpochCreate, universe_id: str, user_id: str) -> Optional[schemas.Epoch]:
    from llm.client import get_llm_client
    import json

    # 1. Inheritance Protocol: Fetch previous Epoch's stances
    prev_epoch_res = db.table("Epochs").select("character_stances")\
        .eq("universe_id", universe_id)\
        .order("id", desc=True)\
        .limit(1)\
        .execute()
    
    inherited_stances = {}
    if prev_epoch_res.data:
        inherited_stances = prev_epoch_res.data[0].get('character_stances') or {}

    # 2. Genesis Event: Extract new stances from seed prose, if provided
    newly_extracted_stances = {}
    if epoch_data.seed_prose:
        llm = get_llm_client()
        prompt = f"""
        Read the following text. Identify all characters. For each character, extract their name and a one-sentence description of their core personality or stance.
        Return ONLY a JSON object of the format {{"character_name": "stance"}}.
        If no characters are found, return an empty JSON object {{}}.
        
        Text:
        ---
        {epoch_data.seed_prose[:4000]}
        ---
        
        JSON Output:
        """
        try:
            response = llm.chat_completion(prompt)
            cleaned_response = response.strip().replace('`', '').replace('json', '')
            newly_extracted_stances = json.loads(cleaned_response)
        except Exception as e:
            logger.error(f"Failed to extract character stances from seed prose: {e}")
            # Do not halt creation, just proceed with inherited stances

    # 3. Merge Stances (Inherited -> Payload -> Extracted)
    # This allows manual override from payload, but adds new characters from prose.
    payload_stances = epoch_data.character_stances or {}
    final_stances = {**inherited_stances, **payload_stances, **newly_extracted_stances}
    
    insert_data = epoch_data.model_dump()
    insert_data["universe_id"] = universe_id
    insert_data["character_stances"] = final_stances # Override with merged dict
    
    # 4. Create
    res = db.table("Epochs").insert(insert_data).execute()
    return schemas.Epoch(**res.data[0]) if res.data else None

def update_epoch(db: Client, epoch_id: int, epoch_data: schemas.EpochUpdate, user_id: str) -> Optional[schemas.Epoch]:
    update_data = epoch_data.model_dump(exclude_unset=True)
    res = db.table("Epochs").update(update_data).eq("id", epoch_id).execute()
    return schemas.Epoch(**res.data[0]) if res.data else None

def get_latent_atom_count(db: Client, universe_id: str, user_id: str) -> int:
    try:
        res = db.rpc("get_latent_count", {"p_universe_id": universe_id, "p_user_id": user_id}).execute()
        return res.data[0]['latent_atom_count'] if res.data else 0
    except Exception: return 0

def get_all_atoms_for_universe(db: Client, universe_id: str, user_id: str) -> List[schemas.Atom]:
    res = db.table("Atoms").select("*").eq("universe_id", universe_id).execute()
    return [schemas.Atom(**a) for a in res.data]

def patch_atom_discovery_epoch(db: Client, atom_id: str, new_discovery_epoch_id: int, user_id: str) -> Optional[schemas.Atom]:
    update_data = {"discovery_epoch_id": new_discovery_epoch_id}
    res = db.table("Atoms").update(update_data).eq("id", atom_id).execute()
    return schemas.Atom(**res.data[0]) if res.data else None

def delete_volume(db: Client, volume_id: str):
    """
    Deletes a StoryVolume and all its associated data (Nodes, Edges, Atoms).
    The order of deletion is important to respect foreign key constraints.
    """
    try:
        # 1. Delete Edges associated with the volume
        db.table("Edges").delete().eq("volume_id", volume_id).execute()
        
        # 2. Delete Nodes associated with the volume
        db.table("Nodes").delete().eq("volume_id", volume_id).execute()

        # 3. Delete Atoms that were crystallized from this volume
        db.table("Atoms").delete().eq("source_volume_id", volume_id).execute()
        
        # 4. Finally, delete the volume itself
        db.table("StoryVolumes").delete().eq("id", volume_id).execute()
        
        logger.info(f"Successfully deleted volume {volume_id} and all associated data.")
        return True
    except Exception as e:
        logger.error(f"Error during cascading delete for volume {volume_id}: {e}")
        # Re-raise the exception to be caught by the API endpoint
        raise e

# --- 5. UTILITY ---
def get_project_members(db: Client, project_id: str) -> List[dict]:
    res = db.table("project_members").select("user_id, profiles(username, avatar_url)").eq("project_id", project_id).execute()
    return res.data

def get_style_samples(db: Client, user_id: str, limit: int = 3) -> List[str]:
    """
    Retrieves the most recent writing samples (video_script, seed_prose, crystallized_thought)
    to be used as style injection context.
    """
    try:
        # Search for atoms that represent finished writing
        res = db.table("Atoms").select("content")\
            .eq("user_id", user_id)\
            .in_("type", ["video_script", "seed_prose", "crystallized_thought"])\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return [r['content'] for r in res.data if r.get('content')]
    except Exception as e:
        logger.error(f"Error fetching style samples: {e}")
        return []