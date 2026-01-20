from celery import Celery
from sqlalchemy.orm import Session
from llm.client import LLMClient

class BaseAgent:
    """
    Base class for all agents, providing common dependencies.
    """
    def __init__(self, db: Session, worker: Celery, llm: LLMClient):
        self.db = db
        self.worker = worker
        self.llm = llm
