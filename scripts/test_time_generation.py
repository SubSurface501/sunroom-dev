import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Configure Celery
broker_url = os.environ.get("CELERY_BROKER_URL", "pyamqp://guest@localhost//")
celery_app = Celery('sunroom_tasks', broker=broker_url, backend='rpc://')

USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" # From previous step

def dispatch_time_test():
    print(f"Dispatching Time Traveler Tests for User {USER_ID}")
    
    # Run A: The Ghost (2020)
    # Time Range: 2020-01-01 to 2020-12-31
    task_a = celery_app.send_task(
        'agents.pipeline.draft_volume_structure', 
        args=[
            USER_ID, 
            "The Future of AI", 
            "Machine Consciousness",
            ["AI Philosophy"], # Lens
            {"start": "2020-01-01T00:00:00Z", "end": "2020-12-31T23:59:59Z"} # Time Range
        ]
    )
    print(f"Task A (2020) Dispatched: {task_a.id}")

    # Run B: The Living (2024)
    # Time Range: 2024-01-01 to 2024-12-31
    task_b = celery_app.send_task(
        'agents.pipeline.draft_volume_structure', 
        args=[
            USER_ID, 
            "The Future of AI", 
            "Machine Consciousness",
            ["AI Philosophy"], # Lens
            {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"} # Time Range
        ]
    )
    print(f"Task B (2024) Dispatched: {task_b.id}")

if __name__ == "__main__":
    dispatch_time_test()
