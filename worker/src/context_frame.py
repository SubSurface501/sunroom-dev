from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

# --- 1. THE WORLD BIBLE (Immutable Laws) ---
class EntityType(str, Enum):
    CHARACTER = "character"
    FACTION = "faction"
    LOCATION = "location"
    OBJECT = "object"
    BUILDING = "building"
    WILDERNESS = "wilderness"
    ANOMALY = "anomaly"
    TRANSITION_POINT = "transition_point"

class WorldLaw(BaseModel):
    name: str
    description: str
    consequences: str # What happens if broken?
    exceptions: Optional[List[str]] = None

class Entity(BaseModel):
    name: str
    type: EntityType
    description: str
    is_protagonist: bool = False
    immutable_traits: List[str] # e.g. "Cannot fly", "Hates elves"
    aliases: Optional[List[str]] = Field(default_factory=list, description="Alternative names or pronouns (e.g., 'The Knight', 'She').")
    relationships: Dict[str, str] = {} # "name" -> "relation"
    location_id: Optional[str] = None # Where does this item live? (e.g. "loc_blacksmith")
    is_takeable: bool = True
    price: int = 0 # For economy simulation

class MagicSystem(BaseModel):
    name: str
    rules: List[str]
    costs: List[str]
    limitations: List[str]

class WorldBible(BaseModel):
    """
    The Static Truth of the Universe.
    This does not change during a story, only between Universes/Epochs.
    """
    world_seed: str = "default_seed" # THE ANCHOR for Procedural Generation
    laws: List[WorldLaw] = []
    entities: Dict[str, Entity] = {} # Keyed by normalized name
    magic_system: Optional[MagicSystem] = None
    geography: Dict[str, str] = {} # Location -> Description
    prohibitions: List[str] = [] # Hard banned concepts
    thematic_template: Optional[Dict] = None # V15 - AI-generated themes
    dynamic_rules: List[Dict] = Field(default_factory=list, description="Volume-specific logic predicates compiled by the Architect.")

# --- 2. THE NARRATIVE LEDGER (Hybrid State) ---
class QuestState(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    DORMANT = "dormant"

class Quest(BaseModel):
    id: str
    title: str
    status: QuestState
    steps_completed: List[str] = []
    next_step: Optional[str] = None

class HardState(BaseModel):
    """
    PHYSICS ENGINE CONTROLLED.
    The LLM cannot hallucinate changes here. Python updates this.
    """
    current_location_id: str = "loc_start"
    current_time: int = 0
    inventory: List[str] = []
    traits: List[str] = [] # e.g. ["blue_essence_aura", "injured"]
    health: int = 100
    active_quests: Dict[str, Quest] = {}

class SoftState(BaseModel):
    """
    LLM CONTROLLED (The "Self-Correction Bridge").
    Tracks psychological, social, and abstract variables.
    """
    mood: str = "Neutral"
    relationships: Dict[str, float] = {} # "King" -> 0.5 (Neutral)
    reputation: Dict[str, str] = {} # "Town" -> "Hero"
    narrative_flags: Dict[str, bool] = {} # "knows_secret" -> True

class NarrativeLedger(BaseModel):
    """
    The Dynamic State of the Story.
    Splits rigid physics from fluid narrative.
    """
    hard_state: HardState = Field(default_factory=HardState)
    soft_state: SoftState = Field(default_factory=SoftState)

    # Compatibility properties for legacy code that expects flattened fields
    @property
    def current_location(self): return self.hard_state.current_location_id
    @property
    def current_time(self): return str(self.hard_state.current_time)
    @property
    def inventory(self): return self.hard_state.inventory
    @property
    def character_states(self): return {"health": str(self.hard_state.health), "mood": self.soft_state.mood}

# --- 3. THE PERCEPTION MANIFEST (Structured Latent State) ---
class PerceptionManifest(BaseModel):
    """
    What the character SEES, HEARS, and FEELS right now.
    Aggregates:
    1. Static Proc-Gen Environment (from Hash)
    2. Dynamic Hard State (items on floor, open doors)
    3. Internal Soft State (mood, vibes)
    """
    location_visuals: Dict[str, str] # "atmosphere": "damp", "feature": "stalactite"
    visible_entities: List[str] # ["Goblin (Dead)", "Chest (Open)"]
    sensory_details: Dict[str, str] # "sound": "dripping water", "smell": "iron"
    character_internal_state: str # "You feel anxious."
    available_actions: List[str] # ["Open Chest", "Leave North"] (Hint for LLM)

# --- 4. THE CONTEXT FRAME (The Active Window) ---
class ContextFrame(BaseModel):
    """
    The specific slice of reality relevant to the CURRENT SCENE.
    Constructed by the System before the LLM writes a word.
    """
    # 1. The Rules (Selected from Bible)
    active_laws: List[WorldLaw]
    local_geography: str # Description of WHERE we are
    present_entities: List[Entity] # Who is here?
    
    # 2. The State (From Ledger)
    ledger_snapshot: NarrativeLedger
    
    # 3. The Story (From Graph)
    previous_context: str # Summary of last 3 nodes
    immediate_goal: str # The specific objective of this scene
    termination_condition: str # When to stop
    
    # 4. The Constraints (Computed)
    required_inclusions: List[str] # Things that MUST be mentioned
    forbidden_concepts: List[str] # Things that MUST NOT be mentioned
    
    def to_prompt_block(self) -> str:
        """
        Renders the frame into a rigid string for the LLM System Prompt.
        """
        laws_str = "\n".join([f"- {l.name}: {l.description} (CONSEQUENCE: {l.consequences})" for l in self.active_laws])
        entities_str = "\n".join([f"- {e.name}: {e.description} (TRAITS: {', '.join(e.immutable_traits)})" for e in self.present_entities])
        inventory_str = ", ".join(self.ledger_snapshot.inventory) if self.ledger_snapshot.inventory else "None"
        
        return f"""
*** CONTEXT FRAME (THE IMMUTABLE TRUTH OF THIS SCENE) ***

[1] THE LAWS OF PHYSICS & MAGIC (ABSOLUTE):
{laws_str}

[2] THE STAGE (WHERE & WHO):
LOCATION: {self.ledger_snapshot.current_location} - {self.local_geography}
PRESENT ACTORS:
{entities_str}

[3] THE STATE (STARTING CONDITION):
TIME: {self.ledger_snapshot.current_time}
INVENTORY: {inventory_str}
CONDITION: {self.ledger_snapshot.character_states}

[4] THE OBJECTIVE:
GOAL: {self.immediate_goal}
STOP WHEN: {self.termination_condition}

[5] HARD CONSTRAINTS:
MUST INCLUDE: {self.required_inclusions}
FORBIDDEN: {self.forbidden_concepts}
*** END CONTEXT FRAME ***
"""
