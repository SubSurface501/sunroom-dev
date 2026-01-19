import os
import json
import shutil
import logging
import traceback
from db.session import get_db
from dotenv import load_dotenv

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compiler")
load_dotenv()

def compile_volume_to_html(volume_id: str):
    db = get_db()
    logger.info(f"Compiling Volume: {volume_id}")

    # 1. Fetch Volume Graph Structure
    try:
        logger.info("Fetching StoryVolume...")
        vol_res = db.table("StoryVolumes").select("*" ).eq("id", volume_id).single().execute()
        
        if not vol_res.data:
            logger.error("Volume not found")
            return
            
        volume = vol_res.data
        logger.info("Volume data fetched.")
        
        graph = volume.get('graph_structure', {})
        logger.info(f"Graph type: {type(graph)}")
        
        connections = graph.get('connections', [])
        logger.info(f"Connections type: {type(connections)}")
        
        raw_node_map = graph.get('node_id_map', {})
        logger.info(f"Node Map: {raw_node_map}")
        
        node_map = {}
        for k, v in raw_node_map.items():
            if isinstance(v, str):
                node_map[k] = v
            else:
                logger.warning(f"Skipping invalid map entry: {k}={v}")

        logger.info("Inverting node map...")
        real_to_blueprint = {v: k for k, v in node_map.items()}
        logger.info("Node map inverted.")
        
    except Exception as e:
        logger.error(f"Error fetching volume: {e}")
        traceback.print_exc() # Print full stack trace
        return

    # 2. Fetch All Nodes
    try:
        logger.info("Fetching Trailheads...")
        nodes_res = db.table("Trailheads").select("*" ).eq("volume_id", volume_id).execute()
        nodes = nodes_res.data
        logger.info(f"Fetched {len(nodes)} nodes.")
    except Exception as e:
        logger.error(f"Error fetching nodes: {e}")
        traceback.print_exc()
        return

    # 3. Setup Output Directory
    root_output_dir = os.path.join(os.getcwd(), "worker", "output", "html_book", volume_id)
    assets_dir = os.path.join(root_output_dir, "images")
    os.makedirs(assets_dir, exist_ok=True)
    
    # CSS for the book
    css = """
    <style>
        body { font-family: 'Georgia', serif; background-color: #f4e4bc; color: #333; margin: 0; padding: 20px; text-align: center; }
        .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 40px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .page { margin-bottom: 40px; border-bottom: 1px solid #ddd; padding-bottom: 20px; }
        .page-img { max-width: 100%; height: auto; border: 5px solid #333; margin: 20px 0; }
        .page-text { font-size: 1.2em; line-height: 1.6; text-align: left; }
        .choices { margin-top: 40px; padding-top: 20px; border-top: 2px solid #333; }
        .btn { display: inline-block; background: #333; color: #fff; padding: 15px 30px; text-decoration: none; font-size: 1.1em; margin: 10px; border-radius: 5px; transition: background 0.3s; }
        .btn:hover { background: #555; }
        h1 { font-family: 'Courier New', monospace; text-transform: uppercase; letter-spacing: 2px; }
    </style>
    """

    # 4. Generate HTML for each Node
    for node in nodes:
        node_id = node['id']
        title = node.get('title', 'Untitled Scene')
        content = node.get('content', {})
        pages = content.get('pages', [])
        
        # Identify connections from this node
        my_blueprint_id = real_to_blueprint.get(node_id)
        my_choices = []
        
        # DEBUG: Trace connection logic
        logger.info(f"Processing Node: {node_id} (Blueprint: {my_blueprint_id})")
        
        if my_blueprint_id:
            for conn in connections:
                # logger.info(f"Checking connection from {conn.get('from')} to {conn.get('to')}")
                if conn.get('from') == my_blueprint_id:
                    target_blueprint_id = conn.get('to')
                    target_real_id = node_map.get(target_blueprint_id)
                    label = conn.get('choice_label', 'Next')
                    
                    if target_real_id:
                        my_choices.append({"id": target_real_id, "label": label})
                    else:
                        logger.warning(f"Target node {target_blueprint_id} not found in map!")
        else:
            logger.warning(f"Node {node_id} has no blueprint ID mapping!")
        
        logger.info(f"Node {node_id} has {len(my_choices)} choices. Choices: {my_choices}") # NEW DEBUG LINE

        # HTML Structure
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            {css}
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>
        """

        # Render Pages & Copy Images
        for page in pages:
            page_num = page.get('page_number')
            text = page.get('narrative_text', '')
            
            # Source Path
            src_filename = f"page_{page_num:02d}.png"
            src_path = os.path.join(os.getcwd(), "worker", "output", "images", node_id, src_filename)
            
            # Dest Path
            dest_filename = f"{node_id}_page_{page_num:02d}.png"
            dest_path = os.path.join(assets_dir, dest_filename)
            
            # Copy File
            img_rel_path = ""
            if os.path.exists(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                    img_rel_path = f"images/{dest_filename}"
                except Exception as e:
                    logger.warning(f"Failed to copy image {src_path}: {e}")
            else:
                logger.warning(f"Image not found: {src_path}")
            
            html_content += f"""
            <div class="page">
                {f'<img src="{img_rel_path}" class="page-img" alt="Page {page_num}">' if img_rel_path else '<p>[Image Missing]</p>'}
                <div class="page-text">{text}</div>
            </div>
            """

        # Render Choices
        html_content += '<div class="choices">'
        if my_choices:
            html_content += "<h3>What do you do?</h3>"
            for choice in my_choices:
                html_content += f'<a href="{choice["id"]}.html" class="btn">{choice["label"]}</a>'
        else:
            html_content += "<h3>The End.</h3>"
            html_content += '<a href="start.html" class="btn">Restart</a>'
        
        html_content += '</div></div></body></html>'

        # Save HTML
        filename = f"{node_id}.html"
        filepath = os.path.join(root_output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"Generated: {filepath}")

    # 5. Generate Start Page
    root_node_id = None
    if graph.get('nodes'):
        for n in graph['nodes']:
            if n.get('type') == 'root':
                root_node_id = node_map.get(n['node_id'])
                break
    
    if root_node_id:
        with open(os.path.join(root_output_dir, "start.html"), 'w') as f:
            f.write(f'<script>window.location.href = "{root_node_id}.html";</script>')
        logger.info(f"Start page created redirecting to {root_node_id}")
    
    print(f"\n--- BOOK COMPILED ---")
    print(f"Open this file in your browser to start reading:")
    print(f"{os.path.join(root_output_dir, 'start.html')}")

if __name__ == "__main__":
    volume_id = "baf8c4a0-cb4e-425f-bdc3-98c23eb2157d" 
    compile_volume_to_html(volume_id)
