import logging
from typing import Tuple, Dict, Any, List
from worker.src.simulation.actions import ActionType, ActionResult, MoveAction, TakeAction, DropAction, AttackAction, SpeakAction, InspectAction, UseAction, SiphonAction, ActivateAction
from worker.src.context_frame import NarrativeLedger, HardState, Entity, EntityType, WorldBible
from worker.src.simulation.procedural import ProceduralGenerator

logger = logging.getLogger(__name__)

class PhysicsEngine:
    """
    The Immutable Logic Core.
    Executes actions against the Hard State.
    Returns Success/Fail and State Updates.
    NO LLM CALLS ALLOWED HERE.
    """
    def __init__(self, bible: WorldBible):
        self.bible = bible
        self.procedural = ProceduralGenerator(bible.world_seed, bible=bible)

    def execute_action(self, state: NarrativeLedger, action: ActionType) -> Tuple[NarrativeLedger, ActionResult]:
        """
        Dispatches the action to the correct handler.
        Returns a NEW Ledger (State is immutable-ish) and the Result.
        """
        # Create a copy of the hard state to modify
        # (In a real app, use deepcopy, but Pydantic copy() is shallow-ish, so be careful with nested dicts)
        # For MVP, we modify in place and return the same object, but the pattern implies a transition.
        new_ledger = state.model_copy(deep=True)
        
        handler_map = {
            "move": self._handle_move,
            "take": self._handle_take,
            "drop": self._handle_drop,
            "attack": self._handle_attack,
            "speak": self._handle_speak,
            "inspect": self._handle_inspect,
            "use": self._handle_use,
            "siphon": self._handle_siphon,
            "activate": self._handle_activate
        }
        
        handler = handler_map.get(action.action_type)
        if not handler:
            return state, ActionResult(success=False, message=f"Unknown action type: {action.action_type}")
            
        try:
            result = handler(new_ledger, action)
            # Tick the clock for every action (except maybe Inspect?)
            new_ledger.hard_state.current_time += 1
            return new_ledger, result
        except Exception as e:
            logger.error(f"Physics Crash: {e}")
            return state, ActionResult(success=False, message=f"The universe rejected that action: {str(e)}")

    # --- ACTION HANDLERS ---

    def _handle_move(self, ledger: NarrativeLedger, action: MoveAction) -> ActionResult:
        target_loc = action.target_id
        current_loc = ledger.hard_state.current_location_id
        
        # 1. V9.8 REGION LOCK (Spatial Fencing)
        # Get region for both locations from the procedural generator
        current_region_details = self.procedural.generate_location_details(current_loc)
        target_region_details = self.procedural.generate_location_details(target_loc)
        
        curr_r = current_region_details.get('region')
        targ_r = target_region_details.get('region')

        if curr_r != targ_r:
            # V13 - Wildcard bypass for the primary region
            if curr_r != "primary_region" and targ_r != "primary_region":
                raise ValueError(f"Region Lock Violation: Cannot move from {curr_r} to {targ_r}.")

        # 2. Check Locks
        # Example: 'loc_throne_room' requires 'item_royal_seal'
        if target_loc == "loc_throne_room" and "item_royal_seal" not in ledger.hard_state.inventory:
             return ActionResult(success=False, message="The door is locked. You need the Royal Seal.")

        # 3. Success - Generate Sensory Data from Hash
        ledger.hard_state.current_location_id = target_loc
        
        return ActionResult(
            success=True, 
            message=f"Moved to {target_loc}.", 
            state_changes=["current_location_id"],
            sensory_data={
                "visual": f"The area is {target_region_details['atmosphere']}.",
                "feature": f"You see {target_region_details['feature']}.",
                "structural_integrity": target_region_details['structural_integrity']
            }
        )

    def _handle_take(self, ledger: NarrativeLedger, action: TakeAction) -> ActionResult:
        item_id = action.target_id
        entity = self.bible.entities.get(item_id)

        # V14.7 - Royal Requisition & Predicate Engine
        protagonist = next((p for p in self.bible.entities.values() if (p.get('is_protagonist') if isinstance(p, dict) else getattr(p, 'is_protagonist', False))), None)
        can_requisition = False
        if self.bible.dynamic_rules:
            for rule in self.bible.dynamic_rules:
                if rule.get("bypass") == "price_check":
                    rule_traits = [t.lower() for t in rule.get("traits", [])]
                    p_traits = [t.lower() for t in (protagonist.get('immutable_traits', []) if isinstance(protagonist, dict) else getattr(protagonist, 'immutable_traits', []))]
                    if protagonist and any(trait in p_traits for trait in rule_traits):
                        can_requisition = True
                
                if rule.get("allow_action") == "take" and entity:
                    condition_str = rule.get("if")
                    if not condition_str: continue
                    try:
                        target_str, method_str = condition_str.split('.', 1)
                        method, value = method_str.split('(', 1)
                        value = value.strip(")'\"")
                        condition_met = False
                        if target_str == "location" and method == "has_trait":
                            loc_details = self.procedural.generate_location_details(ledger.hard_state.current_location_id)
                            loc_tags = [loc_details.get("type")]
                            if value in loc_tags:
                                condition_met = True
                        
                        if condition_met and any(tag in entity.immutable_traits for tag in rule.get("tags", [])):
                            ledger.hard_state.inventory.append(item_id)
                            return ActionResult(success=True, message=f"Acquired {item_id} from the location.", state_changes=["inventory"])
                    except Exception as e:
                        logger.warning(f"Failed to parse or apply 'take' rule '{rule}': {e}")

        # --- V14.8: Thematic Forgiveness & Existence Check ---
        virtual_stock = self.procedural.generate_virtual_inventory(ledger.hard_state.current_location_id)
        
        # 1. Strict Check: Is the item explicitly in the bible or virtual stock?
        if not entity and item_id not in virtual_stock:
            # 2. Thematic Forgiveness: Check for partial matches or naming drift.
            for stock_item in virtual_stock:
                if item_id in stock_item or stock_item in item_id:
                    logger.info(f"Thematic Forgiveness: AI requested '{item_id}', found thematic item '{stock_item}'. Approving take.")
                    if stock_item not in ledger.hard_state.inventory:
                        ledger.hard_state.inventory.append(stock_item)
                    return ActionResult(success=True, message=f"Acquired {stock_item}.", state_changes=["inventory"])
            
            # 3. If still not found, then it's truly not here.
            return ActionResult(success=False, message=f"There is no '{item_id}' here.")

        # --- Standard Validation ---
        if entity and getattr(entity, 'type', None) != EntityType.OBJECT:
            return ActionResult(success=False, message=f"You cannot pick up {item_id}.")

        if entity and getattr(entity, 'location_id', None) and entity.location_id != ledger.hard_state.current_location_id:
             if item_id not in virtual_stock:
                 return ActionResult(success=False, message=f"The {entity.name} is not here. It is located at {entity.location_id}.")
        
        item_price = getattr(entity, 'price', 0) if entity else 0
        if item_price > 0 and not can_requisition:
            return ActionResult(success=False, message=f"You cannot afford {getattr(entity, 'name', item_id)}. It costs {item_price} gold.")
        
        # --- Success ---
        if item_id not in ledger.hard_state.inventory:
            ledger.hard_state.inventory.append(item_id)
        
        message = f"Acquired {item_id}."
        if can_requisition and item_price > 0:
            message = f"Acquired {item_id} via Royal Requisition."
            
        return ActionResult(success=True, message=message, state_changes=["inventory"])

    def _handle_drop(self, ledger: NarrativeLedger, action: DropAction) -> ActionResult:
        item_id = action.target_id
        
        if item_id in ledger.hard_state.inventory:
            ledger.hard_state.inventory.remove(item_id)
            return ActionResult(success=True, message=f"Dropped {item_id}.", state_changes=["inventory"])
        else:
            return ActionResult(success=False, message=f"You don't have {item_id}.")

    def _handle_attack(self, ledger: NarrativeLedger, action: AttackAction) -> ActionResult:
        target_id = action.target_id
        weapon = action.weapon_id
        
        # 1. Weapon check
        if weapon and weapon not in ledger.hard_state.inventory:
            return ActionResult(success=False, message=f"You don't have the {weapon}.")
            
        # 2. Combat Logic (Simple)
        # In a real system, we'd roll dice.
        return ActionResult(
            success=True, 
            message=f"Attacked {target_id} with {weapon or 'fists'}. It flinched.",
            sensory_data={"sound": "Thud!", "visual": "Impact tremor"}
        )

    def _handle_speak(self, ledger: NarrativeLedger, action: SpeakAction) -> ActionResult:
        # Speaking is always "physically" successful, but might fail socially (Soft State)
        return ActionResult(
            success=True, 
            message=f"Spoke to {action.target_id} about {action.topic}.",
            state_changes=[] 
        )

    def _handle_inspect(self, ledger: NarrativeLedger, action: InspectAction) -> ActionResult:
        # Use procedural generation to give consistent details about locations
        if "loc_" in action.target_id:
             proc_details = self.procedural.generate_location_details(action.target_id)
             return ActionResult(
                success=True,
                message=f"Inspected {action.target_id}.",
                sensory_data={
                    "visual": f"It is {proc_details['atmosphere']}.",
                    "detail": f"Dominating the view is {proc_details['feature']}."
                }
            )
            
        return ActionResult(
            success=True,
            message=f"Inspected {action.target_id}. It seems significant.",
            sensory_data={"detail": "High resolution texture analysis"}
        )

    def _handle_use(self, ledger: NarrativeLedger, action: UseAction) -> ActionResult:
        item_id = action.target_id
        
        # V14 Presence Fix: Allow using entities that are present, not just in inventory.
        # 1. Get the lists of what is nearby and what is owned
        current_inv = ledger.hard_state.inventory
        # This is a simplification; a real engine would get this from a spatial index.
        # For now, we assume bible entities at the same location are "nearby".
        nearby_entities = [e.name.lower() for e in self.bible.entities.values() if e.location_id == ledger.hard_state.current_location_id]

        # 2. Check for presence
        # The protagonist can always use "themselves"
        protagonist = next((p for p in self.bible.entities.values() if p.is_protagonist), None)
        protagonist_names = [protagonist.name.lower()] + [a.lower() for a in protagonist.aliases] if protagonist else []

        if item_id.lower() not in current_inv and item_id.lower() not in nearby_entities and item_id.lower() not in protagonist_names:
            return ActionResult(success=False, message=f"You cannot use {item_id}; it is not here.")
            
        # Get Entity Definition
        entity = self.bible.entities.get(item_id)
        traits = entity.immutable_traits if entity else []
        laws = [l.name for l in self.bible.laws]

        # --- ARCANE INTERACTION LOGIC (GENERIC) ---
        if "arcane_responsive" in traits:
            if "Arcane Science" in laws:
                return ActionResult(success=True, message=f"{item_id} thrums with arcane power, interacting with the target.", sensory_data={"visual": "A burst of violet light."})
            else:
                return ActionResult(success=False, message=f"{item_id} is inert. It seems to be just a mundane object.", sensory_data={"sound": "Clunk."})
                
        # Logic for keys/potions would go here
        return ActionResult(success=True, message=f"Used {item_id}.", state_changes=["inventory"])

    def _handle_siphon(self, ledger: NarrativeLedger, action: SiphonAction) -> ActionResult:
        # Requires Arcane Science
        laws = [l.name for l in self.bible.laws]
        if "Arcane Science" not in laws:
            return ActionResult(success=False, message="Siphoning is physically impossible in this reality.")
            
        return ActionResult(success=True, message=f"Siphoned energy from {action.target_id}.", sensory_data={"visual": "Streams of light flow into you."})

    def _handle_activate(self, ledger: NarrativeLedger, action: ActivateAction) -> ActionResult:
        # Requires Arcane Science or High Tech
        laws = [l.name for l in self.bible.laws]
        if "Arcane Science" not in laws and "High Tech" not in laws:
             return ActionResult(success=False, message="You don't know how to activate this.")
             
        return ActionResult(success=True, message=f"Activated {action.target_id}.", sensory_data={"sound": "Humming noise."})
