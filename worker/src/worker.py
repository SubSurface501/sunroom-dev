from .agents.indexing import IndexAtomAgent
from .agents.scripting import ScriptingAgent
from .agents.youtube_ideation import GeneratePerformanceDrivenIdeasAgent
from .agents.youtube_ingestion import TranscriptAgent

# --- Initialize Agents ---
# We initialize them here so they can reuse the shared clients (DB, LLM)
transcript_agent = TranscriptAgent(db_client=db_client, llm_client=llm_client)
performance_agent = GeneratePerformanceDrivenIdeasAgent(db_client=db_client, llm_client=llm_client)
indexing_agent = IndexAtomAgent(db_client=db_client, llm_client=llm_client)
scripting_agent = ScriptingAgent(db_client=db_client, llm_client=llm_client)


@celery_app.task(name="agents.youtube_ingestion.run")
def run_youtube_ingestion(user_id: str, playlist_ids: list[str] = None):
from src.agents.tasks import worker

# Configure logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("--- worker.py: Starting Celery worker ---")
    worker.start()
