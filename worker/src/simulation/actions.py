from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union

# --- ATOMIC ACTION PRIMITIVES ---

class BaseAction(BaseModel):
    """Base class for all discrete physical actions."""
    action_type: str
    target_id: Optional[str] = Field(None, description="The ID of the object/entity/location being targeted.")

class MoveAction(BaseAction):
    action_type: Literal["move"] = "move"
    target_id: str = Field(..., description="The ID of the location to move to (e.g., 'loc_cave_entrance').")

class TakeAction(BaseAction):
    action_type: Literal["take"] = "take"
    target_id: str = Field(..., description="The ID of the item to pick up.")

class DropAction(BaseAction):
    action_type: Literal["drop"] = "drop"
    target_id: str = Field(..., description="The ID of the item to drop.")

class AttackAction(BaseAction):
    action_type: Literal["attack"] = "attack"
    target_id: str = Field(..., description="The ID of the entity to attack.")
    weapon_id: Optional[str] = Field(None, description="ID of the item used as a weapon.")

class SpeakAction(BaseAction):
    action_type: Literal["speak"] = "speak"
    target_id: str = Field(..., description="The ID of the entity to speak to.")
    topic: str = Field(..., description="The subject of conversation.")
    tone: str = Field("neutral", description="The emotional tone (e.g., 'aggressive', 'pleading').")

class InspectAction(BaseAction):
    action_type: Literal["inspect"] = "inspect"
    target_id: str = Field(..., description="The ID of the object or location to examine closely.")

class UseAction(BaseAction):
    action_type: Literal["use"] = "use"
    target_id: str = Field(..., description="The ID of the item to use (e.g., 'item_potion').")
    target_on_id: Optional[str] = Field(None, description="The ID of the object to use it ON (e.g., 'obj_door').")

class SiphonAction(BaseAction):
    action_type: Literal["siphon"] = "siphon"
    target_id: str = Field(..., description="The ID of the entity/object to siphon energy FROM.")
    target_to_id: Optional[str] = Field(None, description="The ID of the object to transfer energy TO.")

class ActivateAction(BaseAction):
    action_type: Literal["activate"] = "activate"
    target_id: str = Field(..., description="The ID of the artifact to activate.")

# Union type for the Engine to process
ActionType = Union[MoveAction, TakeAction, DropAction, AttackAction, SpeakAction, InspectAction, UseAction, SiphonAction, ActivateAction]

# --- ACTION RESULTS ---

class ActionResult(BaseModel):
    """
    The deterministic outcome of an action.
    This is what the Storybook Agent uses to 'render' the scene.
    """
    success: bool
    message: str = Field(..., description="A physics-level description of the result (e.g. 'Door opened', 'Goblin died').")
    state_changes: List[str] = Field(default=[], description="List of keys in the HardState that changed.")
    sensory_data: Optional[dict] = Field(None, description="Sounds, smells, or visual flashes resulting from the action.")
