import os
import sys
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

# Add the root directory to sys.path to import db and other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase_client
from db import schemas

def compile_series_bible(storyline_id: str, output_file: Optional[str] = None):
    db = get_supabase_client()
    
    print(f"--- Compiling Series Bible for Storyline: {storyline_id} ---")
    
    # 1. Fetch Storyline
    try:
        storyline = None
        # Try exact match if it looks like a UUID
        try:
            uuid.UUID(storyline_id)
            res = db.table("Storylines").select("*").eq("id", storyline_id).execute()
            if res.data:
                storyline = res.data[0]
        except ValueError:
            pass # Not a full UUID
            
        if not storyline:
            # Fetch all and prefix match in Python
            res = db.table("Storylines").select("*").execute()
            matches = [s for s in res.data if s['id'].startswith(storyline_id)]
            
            if not matches:
                print(f"Error: Storyline {storyline_id} not found.")
                return
            
            if len(matches) > 1:
                print(f"Multiple storylines found for prefix {storyline_id}:")
                for s in matches:
                    print(f" - {s['id']} ({s['name']})")
                print("Please provide the full ID.")
                return
            
            storyline = matches[0]
        
        storyline_id = storyline['id']
    except Exception as e:
        print(f"Error fetching storyline: {e}")
        return
    
    universe_id = storyline['universe_id']
    user_id = storyline['user_id']
    
    # 2. Fetch Universe
    universe_res = db.table("Universes").select("*").eq("id", universe_id).single().execute()
    universe = universe_res.data
    
    # 3. Fetch Epochs
    epochs_res = db.table("Epochs").select("*").eq("universe_id", universe_id).order("id").execute()
    epochs = epochs_res.data
    
    # 4. Fetch Atoms for the Universe
    atoms_res = db.table("Atoms").select("*").eq("universe_id", universe_id).execute()
    atoms = atoms_res.data
    
    # 5. Fetch StoryVolumes for the Storyline
    volumes_res = db.table("StoryVolumes").select("*").eq("storyline_id", storyline_id).order("created_at").execute()
    volumes = volumes_res.data
    
    # --- Formatting ---
    
    bible_md = f"# Series Bible: {universe['name']}\n\n"
    bible_md += f"**Storyline ID:** `{storyline['id']}`\n"
    bible_md += f"**Storyline Name:** {storyline['name']}\n"
    if storyline.get('summary'):
        bible_md += f"**Summary:** {storyline['summary']}\n"
    bible_md += "\n---\n\n"
    
    # Universe Section
    bible_md += "## Universe Overview\n"
    if universe.get('description'):
        bible_md += f"{universe['description']}\n\n"
    
    if universe.get('world_bible') and isinstance(universe['world_bible'], dict) and universe['world_bible']:
        bible_md += "### World Bible (Immutable Facts)\n"
        bible_md += "```json\n"
        bible_md += json.dumps(universe['world_bible'], indent=2)
        bible_md += "\n```\n\n"

    # Epochs Section
    bible_md += "## Chronology (Epochs)\n"
    for epoch in epochs:
        bible_md += f"### Epoch {epoch['id']}: {epoch['name']}\n"
        if epoch.get('archetype'):
            bible_md += f"- **Archetype:** {epoch['archetype']}\n"
        if epoch.get('system_anchor'):
            bible_md += f"- **System Anchor:** {epoch['system_anchor']}\n"
        if epoch.get('prohibitions'):
            prohs = epoch['prohibitions']
            if isinstance(prohs, list):
                bible_md += f"- **Prohibitions:** {', '.join(prohs)}\n"
            else:
                bible_md += f"- **Prohibitions:** {prohs}\n"
        
        bible_md += "\n#### Character Stances\n"
        stances = epoch.get('character_stances') or {}
        if stances:
            for char, stance in stances.items():
                bible_md += f"- **{char}**: {stance}\n"
        else:
            bible_md += "_No specific stances recorded for this epoch._\n"
            
        bible_md += "\n#### Narrative Ledger\n"
        ledger = epoch.get('narrative_ledger') or []
        if isinstance(ledger, list):
            for entry in ledger:
                bible_md += f"- {entry}\n"
        elif isinstance(ledger, dict):
             for k, v in ledger.items():
                bible_md += f"- **{k}**: {v}\n"
        else:
             bible_md += f"- {ledger}\n"
        
        if epoch.get('summary'):
            bible_md += f"\n**Epoch Summary:** {epoch['summary']}\n"
        bible_md += "\n---\n"

    # Characters Section (Derived from Atoms and Stances)
    bible_md += "## Characters & Entities\n"
    all_characters = {}
    for epoch in epochs:
        stances = epoch.get('character_stances') or {}
        for char, stance in stances.items():
            all_characters[char] = stance
            
    if all_characters:
        for char, stance in all_characters.items():
            bible_md += f"### {char}\n"
            bible_md += f"**Role/Stance:** {stance}\n\n"
    else:
        bible_md += "_No characters identified._\n\n"
        
    # Atoms Section
    bible_md += "## World Knowledge (Atoms)\n"
    atoms_by_type = {}
    for atom in atoms:
        t = atom['type']
        if t not in atoms_by_type:
            atoms_by_type[t] = []
        atoms_by_type[t].append(atom)
        
    if atoms_by_type:
        for a_type, type_atoms in atoms_by_type.items():
            bible_md += f"### Type: {a_type}\n"
            for atom in type_atoms:
                bible_md += f"- **{atom['name']}**: {atom['content']}\n"
            bible_md += "\n"
    else:
        bible_md += "_No world atoms found for this universe._\n\n"

    # Narrative Prose Section
    bible_md += "## Generated Narrative Volumes\n"
    if volumes:
        for vol in volumes:
            bible_md += f"### Volume: {vol['title']}\n"
            bible_md += f"**Root Concept:** {vol['root_concept']}\n\n"
            
            # --- MANUSCRIPT (Long-form Prose) ---
            manuscript = vol.get('manuscript') or {}
            if manuscript:
                bible_md += "#### Full Manuscript\n"
                # Manuscript is often stored as a dict of node_id -> text or a list
                if isinstance(manuscript, dict):
                    for node_id, text in manuscript.items():
                        bible_md += f"{text}\n\n"
                elif isinstance(manuscript, list):
                    for segment in manuscript:
                        bible_md += f"{segment}\n\n"
                else:
                    bible_md += f"{manuscript}\n\n"
                bible_md += "\n---\n\n"

            # --- NARRATIVE BEATS (Nodes) ---
            nodes_res = db.table("Nodes").select("*").eq("volume_id", vol['id']).order("created_at").execute()
            nodes = nodes_res.data
            
            bible_md += "#### Full Narrative Prose (from Pages)\n"
            if nodes:
                for node in nodes:
                    content = node.get('content') or {}
                    pages = content.get('pages', [])
                    
                    if pages:
                        bible_md += f"##### {node['title']}\n\n"
                        for page in pages:
                            p_text = page.get('narrative_text') or page.get('text')
                            if p_text:
                                bible_md += f"{p_text}\n\n"
                    else:
                        # Fallback to top-level prose/text if pages don't exist
                        p_text = content.get('prose') or content.get('text') or content.get('full_text')
                        if p_text:
                            bible_md += f"##### {node['title']}\n\n"
                            bible_md += f"{p_text}\n\n"
            
            bible_md += "#### Narrative Summaries (Beats)\n"
            if nodes:
                for node in nodes:
                    content = node.get('content') or {}
                    summary = content.get('summary') or "*(No summary)*"
                    bible_md += f"**{node['title']}**\n\n{summary}\n\n"
            else:
                bible_md += "_No nodes found for this volume._\n\n"
                
            bible_md += "---\n\n"
    else:
        bible_md += "_No narrative volumes generated yet._\n\n"

    # Save to file or print
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(bible_md)
        print(f"✅ Series Bible compiled successfully to {output_file}")
    else:
        print(bible_md)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/compile_series_bible.py <storyline_id> [output_file]")
        sys.exit(1)
        
    sid = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else f"series_bible_{sid[:8]}.md"
    compile_series_bible(sid, outfile)
