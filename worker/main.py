import logging
from worker.src.agents.tasks import worker

# Configure logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("--- main.py: Starting Celery worker ---")
    worker.start()
