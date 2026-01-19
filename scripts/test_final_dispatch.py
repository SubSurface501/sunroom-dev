import os
import sys
import logging

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from celery import Celery
import time

# --- Logging Setup ---
# Simple logger to see output
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("final_dispatch_test")
# --- End Logging Setup ---

def run_final_dispatch():
    """
    A minimal Celery client to test the connection to the worker in Docker.
    """
    logger.info("--- STARTING FINAL DISPATCH TEST ---")

    # Minimal Celery app to dispatch task
    # It only needs the broker URL to send the task. The worker handles the rest.
    celery_app = Celery('sunroom-test-client',
                        broker=os.environ.get("CELERY_BROKER_URL"),
                        backend='rpc://') # Must have a backend to get results

    # Use data from a previous run. These IDs may not exist, but that's okay.
    # We are testing if the task EXECUTES at all, not if it succeeds.
    volume_id = "e4023e28-f66e-41c0-80af-a0fa8f9f2f4f"
    node_id = "9bc2520a-30c9-4b7a-851c-21e66b7d0e8f"
    world_bible = {"entities": {"Anya": {"name": "Anya", "is_protagonist": True, "traits": ["Knight of the Realm"]}}, "thematic_template": {}}

    logger.info(f"Dispatching task 'agents.pipeline.write_node_task' for node {node_id}...")

    try:
        # Dispatch the task to the worker running in Docker
        async_result = celery_app.send_task(
            'agents.pipeline.write_node_task',
            args=[node_id, volume_id, world_bible],
            # Add a timeout for the task itself on the worker side
            time_limit=600, # 10 minute hard time limit for the task
            soft_time_limit=580
        )

        logger.info(f"Task dispatched with ID: {async_result.id}. Waiting for result...")

        # Heartbeat polling
        start_time = time.time()
        while not async_result.ready():
            print(".", end="", flush=True)
            time.sleep(15)
            if time.time() - start_time > 900: # 15 minute client-side timeout
                logger.error("\nClient-side timeout waiting for task result.")
                # Attempt to revoke the task to clean up the worker
                async_result.revoke(terminate=True)
                return

        # Once ready, get the result
        if async_result.successful():
            result = async_result.get()
            logger.info("\n--- SUCCESS ---")
            logger.info(f"Result: {result}")
        else:
            logger.error("\n--- TASK FAILED ---")
            # Get the traceback from the worker
            tb = async_result.traceback
            logger.error(f"Task traceback: {tb}")

    except Exception as e:
        logger.error(f"\nAn error occurred while dispatching or waiting for the task: {e}", exc_info=True)


if __name__ == "__main__":
    run_final_dispatch()
