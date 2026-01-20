import logging
import sys
import os
from dotenv import load_dotenv
from celery import Celery
from db.session import get_db
from llm.client import get_llm_client

# Load environment variables from .env file
load_dotenv()

# Import the agents that are part of the MVP
from worker.src.agents.indexing import IndexAtomAgent
from worker.src.agents.scripting import ScriptingAgent
from worker.src.agents.youtube_ideation import GeneratePerformanceDrivenIdeasAgent
from worker.src.agents.youtube_ingestion import IngestYoutubeChannelAgent
from worker.src.agents.narrator_agent import NarratorAgent
from worker.src.agents.storybook import StorybookAgent
from worker.src.agents.illustrator import IllustratorAgent
from worker.src.agents.publisher import PublisherAgent
from worker.src.agents.director import DirectorAgent
from worker.src.agents.biographer import BiographerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("--- agents/tasks.py: Starting execution ---")

# --- Worker Setup ---
broker_url = os.environ.get("CELERY_BROKER_URL", "pyamqp://guest@localhost//")
worker = Celery('sunroom-worker',
                broker=broker_url,
                backend='rpc://',
                include=['worker.src.agents.tasks'])
worker.conf.update(
    worker_pool_restarts=True,
    worker_send_task_events=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # This is the important line for Windows
    worker_forking_enable=False 
)
# --- End Worker Setup ---

@worker.task(name='agents.youtube_ideation.run')
def run_youtube_ideation_agent(user_id: str, youtube_channel_id: str, focus_area: str = None, depth: str = "Beginner"):
    """Celery task to run the YouTube ideation agent."""
    # Construct the absolute path to the .env file.
    # This is necessary because the Celery worker's current directory is not guaranteed.
    # __file__ is in worker/src/agents/, so we go up 3 levels to the project root.
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.youtube_ideation.run' received for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = GeneratePerformanceDrivenIdeasAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, youtube_channel_id=youtube_channel_id, focus_area=focus_area, depth=depth)
    except Exception as e:
        logger.error(f"Error in GeneratePerformanceDrivenIdeasAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.youtube_ingestion.run')
def run_youtube_ingestion_agent(user_id: str):
    """Celery task to run the YouTube ingestion agent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.youtube_ingestion.run' received for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = IngestYoutubeChannelAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id)
    except Exception as e:
        logger.error(f"Error in IngestYoutubeChannelAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.indexing.run')
def run_indexing_agent(source_id: str, user_id: str):
    """Celery task to run the IndexAtomAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.indexing.run' received for source {source_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = IndexAtomAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(source_id=source_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in IndexAtomAgent for source {source_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.scripting.run')
def run_script_generation(trailhead_id: str, user_id: str, focus_area: str = None, depth: str = "Broad"):
    """Celery task to run the ScriptingAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.scripting.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = ScriptingAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(trailhead_id=trailhead_id, user_id=user_id, focus_area=focus_area, depth=depth)
    except Exception as e:
        logger.error(f"Error in ScriptingAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.narrator.run')
def run_narrator_agent(trailhead_id: str, user_id: str):
    """Celery task to run the NarratorAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.narrator.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = NarratorAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(trailhead_id=trailhead_id, user_id=user_id)
    except Exception as e:
        logger.error(f"Error in NarratorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.storybook.run')
def run_storybook_agent(user_id: str, trailhead_id: str = None, source_id: str = None, target_length: int = 12, visual_style: str = "Mystical Realism"):
    """Celery task to run the StorybookAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.storybook.run' received for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = StorybookAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id, source_id=source_id, target_length=target_length, visual_style=visual_style)
    except Exception as e:
        logger.error(f"Error in StorybookAgent for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.illustrator.run')
def run_illustrator_agent(user_id: str, trailhead_id: str, provider: str = "imagen"):
    """Celery task to run the IllustratorAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.illustrator.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = IllustratorAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id, provider=provider)
    except Exception as e:
        logger.error(f"Error in IllustratorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.publisher.run')
def run_publisher_agent(user_id: str, trailhead_id: str):
    """Celery task to run the PublisherAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.publisher.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = PublisherAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id)
    except Exception as e:
        logger.error(f"Error in PublisherAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.director.run')
def run_director_agent(user_id: str, trailhead_id: str):
    """Celery task to run the DirectorAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.director.run' received for trailhead {trailhead_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = DirectorAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, trailhead_id=trailhead_id)
    except Exception as e:
        logger.error(f"Error in DirectorAgent for trailhead {trailhead_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.pipeline.run_full_saga_v2')
def run_full_saga_pipeline_v2(user_id: str, trailhead_id: str, source_id: str = None, target_length: int = 12, visual_style: str = "Graphic Novel"):
    """
    Chains the V2 creative pipeline: Storybook -> Director -> Illustrator -> Narrator -> Publisher
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    logger.info(f"--- Celery task 'agents.pipeline.run_full_saga_v2' received for trailhead {trailhead_id} for user {user_id} ---")

    # Use .si() (immutable signature) to prevent passing the result of the previous task as an argument to the next.
    # We pass state via the Database/Filesystem, not the return value.
    chain = (
        run_storybook_agent.si(user_id=user_id, trailhead_id=trailhead_id, source_id=source_id, target_length=target_length, visual_style=visual_style) |
        run_director_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        run_illustrator_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        # run_narrator_agent.si(user_id=user_id, trailhead_id=trailhead_id) |
        run_publisher_agent.si(user_id=user_id, trailhead_id=trailhead_id)
    )
    return chain()

@worker.task(name='agents.biographer.run')
def run_biographer_agent(user_id: str, source_id: str):
    """Celery task to run the BiographerAgent."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)

    logger.info(f"--- Celery task 'agents.biographer.run' received for source {source_id} for user {user_id} ---")
    db = get_db()
    llm = get_llm_client()
    agent = BiographerAgent(db=db, worker=worker, llm=llm)
    try:
        agent.run_task(user_id=user_id, source_id=source_id)
    except Exception as e:
        logger.error(f"Error in BiographerAgent for source {source_id} for user {user_id}: {e}", exc_info=True)
        raise

@worker.task(name='agents.tasks.hello_world')
def hello_world():
    logger.info("--- Hello World task executed successfully ---")
    return "Hello World"

logger.info("--- Celery tasks have been defined ---")