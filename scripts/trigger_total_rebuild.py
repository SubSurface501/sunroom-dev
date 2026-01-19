import os
import sys
import time
from dotenv import load_dotenv
from celery import Celery

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery('sunroom-worker', broker=broker_url, backend='rpc://', include=['worker.src.agents.tasks'])

def trigger_rebuild(user_id: str, trailhead_id: str):
    print(f"--- Starting TOTAL Rebuild for Trailhead {trailhead_id} ---")
    
    # 1. Trigger Storybook (Writer) - This will rewrite the text with the new Persona constraints
    print(f"[1/4] Triggering Storybook Agent (Rewriting Script)...")
    celery_app.send_task('agents.storybook.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id})
    
    # Note: We can't chain these easily with Celery's send_task without signatures/chains, 
    # but for this manual trigger, we can just rely on the user (you) waiting or estimating time.
    # However, since the Storybook agent updates the DB, the subsequent agents need that DB update.
    # The best way to ensure sequence without complex canvas logic here is to just fire them.
    # BUT, Illustrator reads from DB. If Storybook hasn't finished writing, Illustrator will read the OLD text.
    
    print("!!! IMPORTANT !!!")
    print("The Storybook Agent takes time to write (approx 1-2 mins).")
    print("The Illustrator, Narrator, and Publisher tasks must wait for the Writer to finish.")
    print("I will schedule them with delays.")

    # 2. Trigger Illustrator (Visuals) - Delayed 2 minutes
    print(f"[2/4] Scheduling Illustrator Agent (Visuals) in 2 minutes...")
    celery_app.send_task('agents.illustrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id}, countdown=120)
    
    # 3. Trigger Narrator (Audio) - Delayed 3 minutes (reads from same DB manifest)
    print(f"[3/4] Scheduling Narrator Agent (Audio) in 3 minutes...")
    celery_app.send_task('agents.narrator.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id}, countdown=180)
    
    # 4. Trigger Publisher (PDF) - Delayed 8 minutes (needs images and audio)
    print(f"[4/4] Scheduling Publisher Agent (PDF) in 8 minutes...")
    celery_app.send_task('agents.publisher.run', kwargs={'user_id': user_id, 'trailhead_id': trailhead_id}, countdown=480)
    
    print("--- All tasks dispatched. ---")

if __name__ == "__main__":
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" 
    trailhead_id = "8131ca68-7373-4ab7-9cdd-ebce0f8106cb" 
    
    trigger_rebuild(user_id, trailhead_id)