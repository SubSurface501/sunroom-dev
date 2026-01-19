
import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from celery import Celery

load_dotenv()

# 1. Setup DB
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

# 2. Setup Celery (to send tasks)
celery_app = Celery(
    'sunroom_tasks',
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend='rpc://'
)

def kick_volume(volume_id):
    print(f"--- Kicking Stuck Volume: {volume_id} ---")
    
    # Fetch all nodes
    nodes = supabase.table("Trailheads").select("id, content").eq("volume_id", volume_id).execute().data
    
    requeued_count = 0
    for node in nodes:
        status = node.get('content', {}).get('production_status', 'pending')
        
        if status != 'completed':
            print(f"Re-queueing Node: {node['id']} (Status: {status})")
            # Send task manually
            celery_app.send_task('agents.pipeline.write_node_task', args=[node['id'], volume_id])
            requeued_count += 1
            
    if requeued_count == 0:
        print("All nodes appear complete! Forcing Finalize...")
        celery_app.send_task('agents.pipeline.finalize_volume', args=[None, volume_id])
    else:
        print(f"Re-queued {requeued_count} nodes.")

if __name__ == "__main__":
    # Replace with your stuck Volume ID found in logs: 0196f3cd-db63-4b6f-8ffb-62618af46fe3
    vol_id = "0196f3cd-db63-4b6f-8ffb-62618af46fe3" 
    if len(sys.argv) > 1:
        vol_id = sys.argv[1]
        
    kick_volume(vol_id)
