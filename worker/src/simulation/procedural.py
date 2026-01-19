import hashlib
import random
from typing import List, Dict, Any, Optional
from worker.src.context_frame import WorldBible, EntityType

# V14.6 - Default themes are now a FALLBACK, not the primary source.
DEFAULT_THEMES = {
    "blacksmith": ["rope", "cape", "nails", "hammer", "tongs", "horseshoes", "iron_bar", "whetstone", "axe_head", "shield_boss", "steel_ingot", "charcoal", "bellows", "anvil", "gauntlets", "helmet", "iron_chain", "pincers", "metal_scraps", "coal_bucket"],
    "quartermaster": ["rations", "bandages", "waterskin", "torch", "flint", "backpack", "oil_flask", "dried_meat", "hardtack", "ale_skin", "bedroll", "sewing_kit", "sharpening_stone", "signal_whistle", "tinderbox", "wool_blanket", "soap", "iron_pot", "fishing_hook", "twine"],
    "stable": ["horse", "saddle", "hay", "brush", "oats", "saddlebags", "reins", "horse_blanket", "feed_bag", "curry_comb", "leather_straps", "bucket", "pitchfork", "manure"],
    "apothecary": ["healing_potion", "herbs", "empty_vial", "mortar_pestle", "dried_roots", "poultice", "laudanum", "herbal_tea", "incense", "alembic", "beaker", "glass_stir_rod", "forceps", "scalpel", "unknown_tincture"],
    "library": ["old_scroll", "quill", "ink_pot", "parchment", "ancient_tome", "wax_seal", "spectacles", "book_stand", "letter_opener", "magnifying_glass", "star_chart", "bound_journal", "loose_notes", "abacus"],
    "archives": ["old_scroll", "quill", "ink_pot", "parchment", "historical_records", "maps", "genealogy_charts", "sealed_letters", "codex", "brittle_book", "dusty_ledgers", "royal_decrees", "tax_records", "forgotten_treaty"],
}

class ProceduralGenerator:
    """
    V14.6: Now reads its templates from the World Bible, making it universe-agnostic.
    """
    def __init__(self, world_seed: str, bible: Optional[WorldBible] = None):
        self.world_seed = world_seed
        self.bible = bible if bible else WorldBible()
        # Thematic templates are now loaded from the bible, with a fallback
        self.themes = getattr(self.bible, 'thematic_template', DEFAULT_THEMES)

    def _get_deterministic_rng(self, unique_id: str) -> random.Random:
        """
        Creates a seeded random number generator for a specific entity/location.
        """
        combined_key = f"{self.world_seed}:{unique_id}"
        seed_int = int(hashlib.sha256(combined_key.encode('utf-8')).hexdigest(), 16)
        rng = random.Random(seed_int)
        return rng

    def generate_virtual_inventory(self, location_id: str) -> List[str]:
        """
        V14.6 Thematic Merger: Combines plot-critical items from the WorldBible
        with procedurally generated atmospheric items from the AI-defined template.
        """
        rng = self._get_deterministic_rng(location_id)
        inventory = []

        # 1. Start with plot-critical items explicitly defined in the World Bible for this location
        for entity_id, entity in self.bible.entities.items():
            # V14.7 - Type-Safe Unified Access
            e_loc = entity.get('location_id') if isinstance(entity, dict) else getattr(entity, 'location_id', None)
            e_type = entity.get('type') if isinstance(entity, dict) else getattr(entity, 'type', None)

            if e_loc == location_id and e_type in [EntityType.OBJECT, 'object']:
                if entity_id not in inventory:
                    inventory.append(entity_id)

        # 2. Match the theme from the bible's template and add procedural items
        for theme_key, pool in self.themes.items():
            if theme_key in location_id.lower():
                num_items = rng.randint(3, min(len(pool), 6))
                procedural_items = rng.sample(pool, num_items)
                inventory.extend([item for item in procedural_items if item not in inventory])
                break # Assume first match is best
                
        # 3. Add fully deterministic clutter
        clutter_seed = hashlib.sha256(f"{self.world_seed}:{location_id}:clutter".encode()).hexdigest()
        clutter_val = int(clutter_seed, 16) % 100
        if clutter_val > 80: 
            inventory.append(f"clutter_{clutter_val}")

        return list(set(inventory))

    def generate_location_details(self, location_id: str) -> Dict[str, Any]:
        """
        V14.6: Generates details based on functional types from the WorldBible, not keywords.
        """
        rng = self._get_deterministic_rng(location_id)
        
        # 1. Get the location's functional type from the bible
        # The WorldBible entities are Pydantic models, so use getattr for robustness
        location_entity = self.bible.entities.get(location_id)
        # V14.7 Type-Safe Location Identification
        loc_type = (location_entity.get('type') if isinstance(location_entity, dict) 
                    else getattr(location_entity, 'type', 'generic')) if location_entity else 'generic'

        # 2. V14.6 - Abstract Region Mapping based on functional type
        region = "primary_region" # Default neutral zone
        if loc_type == "building":
            region = "region_alpha"  # The 'Home' or 'Settlement' region
        elif loc_type == "wilderness":
            region = "region_beta"   # The 'Wilderness' region
        elif loc_type == "anomaly": # A new proposed type for dungeons, ruins etc.
            region = "region_gamma"  # The 'Anomalous' region
        elif loc_type == "transition_point":
            region = "primary_region" # Explicitly a bridge

        # 3. Generate atmosphere and features based on type
        atmospheres = {
            "building": ["bustling and grimy", "pristine and golden", "crumbling and ancient"],
            "wilderness": ["sun-dappled", "overgrown and shadowy", "silent and misty"],
            "anomaly": ["oppressive and dark", "echoing with strange noises", "cold and sterile"],
            "generic": ["hazey", "clear", "rainy", "windy"]
        }
        features = {
            "building": ["a central fountain", "a statue of a hero", "a busy market stall", "a guarded gate"],
            "wilderness": ["a twisted oak tree", "a babbling brook", "a ring of mushrooms", "a fallen log"],
            "anomaly": ["a rusty cage", "a pile of bones", "glowing crystals", "a hidden lever"],
            "generic": ["a strange rock", "a forgotten sign", "a lone flower"]
        }

        # Deterministic Selections
        atmosphere = rng.choice(atmospheres.get(loc_type, atmospheres["generic"]))
        feature = rng.choice(features.get(loc_type, features["generic"]))
        
        # Generate some "Latent Objects" that *could* be found here
        # (These aren't in the DB until interacted with, but exist in potential)
        potential_items = []
        if rng.random() > 0.5:
            potential_items.append(f"item_{loc_type}_scrap")
        
        return {
            "region": region,
            "type": loc_type,
            "atmosphere": atmosphere,
            "feature": feature,
            "structural_integrity": round(rng.uniform(0.1, 1.0), 2),
            "latent_id": f"{location_id}_{rng.randint(1000, 9999)}",
            "potential_items": potential_items
        }
