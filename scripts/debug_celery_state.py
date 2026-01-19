
import os
import sys
from celery.result import AsyncResult
from dotenv import load_dotenv
import redis

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Load env vars
load_dotenv()

# Import the worker app definition
from worker.src.agents.tasks import worker

# Check Redis Queue Depth
r = redis.Redis.from_url(os.environ.get("CELERY_BROKER_URL"))
print(f"Redis Queue Length: {r.llen('celery')}")

# Inspect active tasks
i = worker.control.inspect()
active = i.active()
reserved = i.reserved()

print("\n--- Active Tasks ---")
if active:
    for worker_name, tasks in active.items():
        print(f"Worker: {worker_name}")
        for task in tasks:
            print(f"  - {task['name']} (id={task['id']}) args={task['args']}")
else:
    print("No active tasks.")

print("\n--- Reserved Tasks ---")
if reserved:
    for worker_name, tasks in reserved.items():
        print(f"Worker: {worker_name}")
        for task in tasks:
            print(f"  - {task['name']} (id={task['id']})")
else:
    print("No reserved tasks.")
