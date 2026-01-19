#!/usr/local/bin/python
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import subprocess

# Explicitly add /app to sys.path to ensure modules are found
sys.path.insert(0, '/app')

# --- CONFIGURATION ---
CELERY_APP = "worker.src.agents.tasks"
CONCURRENCY = os.environ.get("CELERYD_CONCURRENCY", "1")

if __name__ == "__main__":
    cmd = [
        "celery",
        "-A", CELERY_APP,
        "worker",
        "--loglevel=info",
        f"--concurrency={CONCURRENCY}"
    ]
    
    print(f"Executing command: {' '.join(cmd)}", flush=True)
    os.execvp(cmd[0], cmd)
