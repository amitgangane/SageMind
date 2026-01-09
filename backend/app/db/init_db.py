from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine

# Import all models so they are registered with Base.metadata
from app.models.document import Document, Chunk  # noqa: F401
from app.models.chat import ChatSession, Message  # noqa: F401


def init_db():
    """Initialize database: create pgvector extension and all tables."""
    with engine.connect() as conn:
        # Enable pgvector extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)
