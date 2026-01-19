from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr

# --- Core Enums ---
class AtomType(str, Enum):
    CONCEPT = "concept"
    INSIGHT = "insight"
    QUESTION = "question"
    VISUAL_ARTIFACT = "visual_artifact"
    STORY_NODE = "story_node"
    THOUGHT = "thought"
    CITATION = "citation" # New type for Librarian
    SEED_PROSE = "seed_prose"

class PermanenceType(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    ARCHETYPAL = "archetypal"

class SourceType(str, Enum):
    YOUTUBE_TRANSCRIPT = "youtube_transcript"
    PERSONAL_JOURNAL = "personal_journal"
    UPLOADED_TEXT = "uploaded_text"
    WEB_SCRAPE = "web_scrape"
    YOUTUBE_VIDEO = "youtube_video"

# --- Base Schemas ---
class Atom(BaseModel):
    id: Optional[str] = None # UUID from Supabase
    user_id: str
    name: str
    type: AtomType = AtomType.CONCEPT
    content: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    created_at_source: Optional[datetime] = None
    epoch_label: Optional[str] = None
    original_author: Optional[str] = None
    resolution_source_id: Optional[str] = None
    discovery_epoch_id: Optional[int] = None # New Epoch field
    # New Universe fields
    universe_id: Optional[str] = None
    storyline_id: Optional[str] = None
    source_volume_id: Optional[str] = None
    permanence: PermanenceType = PermanenceType.DYNAMIC

class AtomCreate(Atom):
    pass

class AtomUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AtomType] = None
    content: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict] = None
    created_at_source: Optional[datetime] = None
    epoch_label: Optional[str] = None
    original_author: Optional[str] = None
    resolution_source_id: Optional[str] = None
    discovery_epoch_id: Optional[int] = None # New Epoch field
    # New Universe fields
    universe_id: Optional[str] = None
    storyline_id: Optional[str] = None
    source_volume_id: Optional[str] = None
    permanence: Optional[PermanenceType] = None

class Source(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    storage_path: str # Changed from file_path
    metadata: Dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    is_processed: bool = False
    media_duration_seconds: Optional[int] = None
    source_type: Optional[SourceType] = SourceType.UPLOADED_TEXT
    original_publication_date: Optional[datetime] = None
    date_confidence: Optional[float] = None
    author: Optional[str] = None
    category_id: Optional[str] = None # New field

class SourceCreate(Source):
    pass

class SourceUpdate(BaseModel):
    title: Optional[str] = None
    storage_path: Optional[str] = None # Changed from file_path
    metadata: Optional[Dict] = None
    is_processed: Optional[bool] = None
    media_duration_seconds: Optional[int] = None
    source_type: Optional[SourceType] = None
    original_publication_date: Optional[datetime] = None
    date_confidence: Optional[float] = None
    author: Optional[str] = None
    category_id: Optional[str] = None # New field

# --- New Category Schemas ---
class Category(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Trailhead(BaseModel):
    id: Optional[str] = None
    user_id: str
    volume_id: Optional[str] = None
    title: str
    insight: str
    suggested_topic: str
    type: str = "default"
    content: Dict = Field(default_factory=dict) # To store dynamic data like blueprint_id
    created_at: Optional[datetime] = None

class TrailheadCreate(Trailhead):
    pass

# --- UNIVERSE, STORYLINE, VOLUME ---
class Universe(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    active_epoch_id: Optional[int] = None # New Epoch field
    world_bible: Optional[Dict] = Field(default_factory=dict) # NEW: Immutable World Facts
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UniverseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    world_bible: Optional[Dict] = Field(default_factory=dict) # NEW: Immutable World Facts

class UniverseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active_epoch_id: Optional[int] = None # New Epoch field
    world_bible: Optional[Dict] = Field(default_factory=dict) # NEW: Immutable World Facts

class Epoch(BaseModel):
    id: int
    universe_id: str
    name: str
    archetype: Optional[str] = None
    system_anchor: Optional[str] = None
    prohibitions: Optional[List[str]] = None
    seed_prose: Optional[str] = None
    character_stances: Optional[Dict] = Field(default_factory=dict)
    narrative_ledger: Optional[Dict] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class EpochCreate(BaseModel):
    universe_id: Optional[str] = None  # Make this Optional!
    name: str
    archetype: Optional[str] = None
    system_anchor: Optional[str] = None
    prohibitions: Optional[List[str]] = None
    seed_prose: Optional[str] = None
    character_stances: Optional[Dict] = Field(default_factory=dict)
    narrative_ledger: Optional[Dict] = Field(default_factory=dict)

class EpochUpdate(BaseModel):
    name: Optional[str] = None
    archetype: Optional[str] = None
    system_anchor: Optional[str] = None
    prohibitions: Optional[List[str]] = None
    seed_prose: Optional[str] = None
    character_stances: Optional[Dict] = None
    narrative_ledger: Optional[List[str]] = None

class Storyline(BaseModel):
    id: str
    universe_id: str
    user_id: str
    name: str
    summary: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class StorylineCreate(BaseModel):
    universe_id: str
    name: str
    summary: Optional[str] = None

class StoryVolume(BaseModel):
    id: Optional[str] = None
    user_id: str
    project_id: Optional[str] = None # For V7 Collective
    universe_id: Optional[str] = None # New
    storyline_id: Optional[str] = None # New
    title: str
    root_concept: str
    graph_structure: Dict = Field(default_factory=dict)
    status: str = "drafting"
    created_at: Optional[datetime] = None
    manuscript: Optional[Dict] = Field(default_factory=dict)
    visuals: Optional[List[str]] = Field(default_factory=list)
    lenses: Optional[List[str]] = Field(default_factory=list) 
    time_range: Optional[Dict] = Field(default_factory=dict) 

class StoryVolumeCreate(StoryVolume):
    pass

class StoryVolumeUpdate(BaseModel):
    title: Optional[str] = None
    root_concept: Optional[str] = None
    graph_structure: Optional[Dict] = None
    status: Optional[str] = None
    manuscript: Optional[Dict] = None
    visuals: Optional[List[str]] = None
    lenses: Optional[List[str]] = None
    time_range: Optional[Dict] = None
    universe_id: Optional[str] = None
    storyline_id: Optional[str] = None

# --- V7 Collective Schemas ---
class Project(BaseModel):
    id: Optional[str] = None
    name: str
    created_by: str
    created_at: Optional[datetime] = None
    description: Optional[str] = None

class ProjectCreate(Project):
    pass

class ProjectMember(BaseModel):
    project_id: str
    user_id: str
    role: str = "member" # e.g., "admin", "member", "viewer"
    joined_at: Optional[datetime] = None

class ProjectMemberCreate(ProjectMember):
    pass

class ActiveProjectLens(BaseModel):
    project_id: str
    lens_atom_id: str # The ID of the 'seed_prose' atom that defines the lens
    is_active: bool = True
    activated_at: Optional[datetime] = None

class ActiveProjectLensCreate(ActiveProjectLens):
    pass

# --- V6 Auto-Genesis / Lenses Schemas ---
class Lens(BaseModel):
    cluster_id: Optional[str] = None
    cluster_name: str
    seed_atom_id: Optional[str] = None # The atom that represents the 'seed' of this lens
    user_id: str
    created_at: Optional[datetime] = None
    # Add temporal distribution if needed

class LensCreate(Lens):
    pass

# --- Persona Schema ---
class PersonaProfile(BaseModel):
    user_id: str
    profile_json: Dict = Field(default_factory=dict)
    system_prompt_cache: Optional[str] = None
    updated_at: Optional[datetime] = None

class PersonaProfileCreate(PersonaProfile):
    pass

class PersonaProfileUpdate(BaseModel):
    profile_json: Optional[Dict] = None
    system_prompt_cache: Optional[str] = None

# --- Graph Normalization Schemas (NEW) ---
class Node(BaseModel):
    id: Optional[str] = None
    volume_id: str
    branch_id: str # Link to the branch this node belongs to
    title: str
    type: str = "narrative_beat"
    content: Dict = Field(default_factory=dict)
    context_snapshot: Optional[str] = None # The serialized 'story so far' leading to this node
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class NodeCreate(Node):
    pass

class NodeUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[Dict] = None
    context_snapshot: Optional[str] = None

class Edge(BaseModel):
    id: Optional[str] = None
    volume_id: str
    source_node_id: str
    target_node_id: str
    type: str = "direct"
    label: Optional[str] = None # Corresponds to 'choice_label'
    created_at: Optional[datetime] = None

class EdgeCreate(Edge):
    pass

class Branch(BaseModel):
    id: Optional[str] = None
    volume_id: str
    name: str = "main"
    head_node_id: Optional[str] = None
    parent_branch_id: Optional[str] = None
    divergence_point_node_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

class BranchCreate(Branch):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    head_node_id: Optional[str] = None
    parent_branch_id: Optional[str] = None
    divergence_point_node_id: Optional[str] = None
    is_active: Optional[bool] = None

# --- API Request Models ---
class CreateNodeRequest(BaseModel):
    volume_id: str
    parent_node_id: str
    branch_id: str
    title: str
    summary: str
    type: str
    relationship_type: str

class ExpandNodeRequest(BaseModel):
    volume_id: str
    node_id: str
    branch_id: str

# --- Usage Tracking Schemas ---
class UsageLog(BaseModel):
    id: Optional[str] = None
    user_id: str
    project_id: Optional[str] = None
    event_type: str  # e.g., 'audio_ingestion', 'llm_generation', 'image_generation'
    details: Dict = Field(default_factory=dict) # { 'cost': 0.1, 'duration': 600, 'model': 'whisper' }
    created_at: Optional[datetime] = None

class UsageLogCreate(UsageLog):
    pass

class Tier(BaseModel):
    id: Union[str, int, None] = None
    name: str # e.g., Free, Pro, Enterprise
    stripe_price_id: Optional[str] = None # The ID of the price in Stripe
    max_documents: Optional[int] = None # New
    max_volumes: Optional[int] = None # New
    max_audio_minutes: Optional[int] = None
    max_llm_tokens: Optional[int] = None
    max_image_generations: Optional[int] = None
    price_monthly: float
    is_active: bool = True
    created_at: Optional[datetime] = None

class TierCreate(Tier):
    pass

class UserSubscription(BaseModel):
    id: Union[str, int, None] = None
    user_id: str
    tier_id: Union[str, int]
    is_active: bool = True
    start_date: Optional[datetime] = None
    cycle_end_date: datetime # When the quotas reset
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None # The ID of the customer in Stripe
    created_at: Optional[datetime] = None
    # Joined tier details
    tiers: Optional[Tier] = None

class UserSubscriptionCreate(UserSubscription):
    pass

class UserSubscriptionUpdate(BaseModel):
    tier_id: Optional[int] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    cycle_end_date: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None

class UserIntegration(BaseModel):
    id: Optional[str] = None
    user_id: str
    service_name: str
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    scopes: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class QuotaStatus(BaseModel):
    has_quota: bool
    remaining_audio_minutes: Optional[int] = None
    remaining_llm_tokens: Optional[int] = None
    remaining_image_generations: Optional[int] = None
    tier_name: Optional[str] = None