import time
import redis
import os
from contextlib import contextmanager

# Connect to your existing Redis instance
# Parse the hostname from the CELERY_BROKER_URL if available, otherwise default to localhost
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
# Simple parsing logic to extract host/port/db or pass directly if redis-py supports URL
r = redis.from_url(broker_url)

MAX_RPM = 50  # Requests Per Minute allowed by Google
BUCKET_KEY = "gemini_api_bucket"

def acquire_token():
    """
    Uses a Token Bucket algorithm. 
    Returns True if a token was acquired, False if we need to wait.
    """
    current_time = int(time.time())
    
    # 1. Refill the bucket based on time passed
    # Using Redis pipeline for atomicity
    pipe = r.pipeline()
    pipe.get(f"{BUCKET_KEY}:tokens")
    pipe.get(f"{BUCKET_KEY}:last_refill")
    tokens, last_refill = pipe.execute()

    tokens = float(tokens) if tokens else MAX_RPM
    last_refill = int(last_refill) if last_refill else current_time

    # Calculate refill
    seconds_passed = current_time - last_refill
    refill_amount = (seconds_passed / 60.0) * MAX_RPM
    new_tokens = min(MAX_RPM, tokens + refill_amount)

    # 2. Try to consume a token
    if new_tokens >= 1:
        pipe = r.pipeline()
        pipe.set(f"{BUCKET_KEY}:tokens", new_tokens - 1)
        pipe.set(f"{BUCKET_KEY}:last_refill", current_time)
        pipe.execute()
        return True, 0
    else:
        # Calculate how long to wait for the next token
        required_wait = (1.0 - new_tokens) * (60.0 / MAX_RPM)
        return False, required_wait

def rate_limit_wait():
    """Blocking function that waits until a token is available."""
    while True:
        success, wait_time = acquire_token()
        if success:
            return
        time.sleep(max(0.1, wait_time))
