
import asyncio
import os
import sys
from db.supabase_client import get_supabase_client

# Hardcoded IDs from the log (Fallback)
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
DEFAULT_STORYLINE_ID = "edcd3f3e-952b-4553-84fc-75d06f92623b"

async def export_saga(storyline_id):
    print(f"Connecting to Supabase for User: {USER_ID}")
    supabase = get_supabase_client()
    
    # Fetch Volumes
    print(f"Fetching volumes for Storyline: {storyline_id}")
    volumes_response = supabase.table("StoryVolumes")\
        .select("*")\
        .eq("storyline_id", storyline_id)\
        .order("created_at")\
        .execute()
    
    volumes = volumes_response.data
    print(f"Found {len(volumes)} volumes.")

    full_text = f"# The Ardent Knight Saga (V8.5)\n\n"

    for i, vol in enumerate(volumes):
        vol_title = vol.get('title') or vol.get('root_concept') or f"Volume {i+1}"
        print(f"Processing Volume {i+1}: {vol_title} ({vol['id']})")
        
        full_text += f"## Volume {i+1}: {vol_title}\n\n"
        
        nodes_response = supabase.table("Nodes")\
            .select("title, content, type")\
            .eq("volume_id", vol['id'])\
            .order("created_at")\
            .execute()
            
        nodes = nodes_response.data
        print(f"  - Found {len(nodes)} nodes.")
        
        for node in nodes:
            title = node.get('title', 'Untitled')
            content_json = node.get('content') or {}
            
            full_text += f"### {title}\n\n"
            
            if isinstance(content_json, dict) and "pages" in content_json:
                for page in content_json["pages"]:
                    narrative = page.get("narrative_text", "")
                    full_text += f"{narrative}\n\n"
            else:
                full_text += f"{content_json}\n\n"
                
            full_text += "---\n\n"

    output_filename = "ardent_knight_saga_v8_5.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    print(f"Successfully exported prose to {output_filename}")

if __name__ == "__main__":
    target_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STORYLINE_ID
    asyncio.run(export_saga(target_id))
