import os
import sys
from celery import Celery

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables (critical for Celery broker URL)
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '.env')))

# Configure Celery app (must match how it's defined in worker/src/agents/tasks.py)
broker_url = os.environ.get("CELERY_BROKER_URL", "pyamqp://guest@localhost//")
celery_app = Celery('sunroom-worker',
                     broker=broker_url,
                     backend='rpc://')

# User and Channel Information
user_id = "5f24cb5b-8559-44e8-932d-0ce3c4c01bc1"
youtube_channel_id = "UCib63oqkQ7hcbLKIdzEZ3Ug"

# Steerability parameters for testing
focus_area = "AI and Consciousness"
depth = "Pro"

print(f"--- Sending ideation task for user: {user_id} ---")
print(f"--- Focus Area: '{focus_area}', Depth: '{depth}' ---")

# Send the task to the GeneratePerformanceDrivenIdeasAgent
# The agent is 'agents.youtube_ideation.run' in tasks.py
celery_app.send_task('agents.youtube_ideation.run', args=[user_id, youtube_channel_id, focus_area, depth])

print("--- Ideation task sent. Check Celery worker logs. ---")
