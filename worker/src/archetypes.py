# worker/src/archetypes.py

"""
This file defines the foundational "Archetype Definitions" for universes within the system.
An Archetype is a set of fundamental laws, principles, and prohibitions that
govern the reality of a world. This provides a deterministic "physics" for the
AI to follow, preventing lore leakage and ensuring narrative consistency.
"""

ARCHETYPE_DEFINITIONS = {
    "materialist": {
        "name": "Materialist",
        "description": "A world governed by the strict laws of physics. Technology is the only path to power. The supernatural is impossible.",
        "system_anchor": (
            "This is a universe of hard science and tangible reality. All events must have a "
            "plausible scientific or logical explanation. There is no magic, no divine intervention, "
            "and no psychic phenomena. Focus on cause and effect, technological advancement, and "
            "the limitations of the physical world."
        ),
        "prohibitions": [
            "magic", "spell", "miracle", "divine", "supernatural", "psychic",
            "teleportation", "healing potion", "amulet", "enchantment", "curse"
        ],
        "suggestions": [
            "technology", "physics", "engineering", "cybernetics", "chemistry",
            "astronomy", "logic", "computation"
        ]
    },
    "high_fantasy": {
        "name": "High Fantasy",
        "description": "A world of magic, mythical creatures, and epic quests. The laws of reality are malleable and subject to arcane forces.",
        "system_anchor": (
            "This is a universe where magic is a fundamental force of nature. Epic heroes, ancient evils, "
            "and mythical beasts are real. Ground the narrative in classic fantasy tropes. Magic should have "
            "its own rules and costs, but it is a powerful and accepted part of life."
        ),
        "prohibitions": [
            "computer", "internet", "circuit board", "AI", "algorithm", "firearm",
            "spacecraft", "quantum physics"
        ],
        "suggestions": [
            "magic", "spell", "dragon", "elf", "dwarf", "quest", "prophecy",
            "kingdom", "artifact", "mana"
        ]
    },
    "cyberpunk": {
        "name": "Cyberpunk",
        "description": "A high-tech, low-life future. Society is dominated by mega-corporations and advanced technology, particularly cybernetics and AI.",
        "system_anchor": (
            "This is a dystopian near-future. Focus on the social impact of technology. "
            "Explore themes of transhumanism, corporate control, and digital consciousness. "
            "Technology is pervasive but often gritty and unreliable. Magic and the supernatural are non-existent."
        ),
        "prohibitions": [
            "magic", "spell", "fantasy", "elf", "dragon", "divine", "miracle"
        ],
        "suggestions": [
            "cybernetics", "megacorporation", "hacker", "netrunner", "AI",
            "dystopia", "neon", "augmentations", "neural interface"
        ]
    },
    "arcane_science": {
        "name": "Arcane Science",
        "description": "A world where magic and technology have merged. The supernatural is studied and manipulated with scientific rigor.",
        "system_anchor": (
            "This universe treats magic as a new field of physics. 'Imbuement', 'runic computation', and "
            "'alchemical engineering' are fields of study. The fantastic is analyzed and industrialized. "
            "Blend the language of science with the outcomes of fantasy."
        ),
        "prohibitions": [
            "divine intervention", "unexplained miracles"
        ],
        "suggestions": [
            "arcanum", "aether", "imbued", "runic", "alchemical", "technomancy",
            "ley lines", "mana reactor"
        ]
    }
}

DEFAULT_ARCHETYPE = "materialist" # Set a default archetype

def get_all_archetypes():
    """Returns a list of all available archetype definitions."""
    return list(ARCHETYPE_DEFINITIONS.values())

def get_archetype(name: str):
    """Returns a specific archetype by its key name."""
    return ARCHETYPE_DEFINITIONS.get(name.lower())