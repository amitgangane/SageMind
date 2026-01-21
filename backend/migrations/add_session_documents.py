"""
Migration to add session_documents association table for Many-to-Many relationship.
Run this once to update existing database schema.
"""
from sqlalchemy import text
from app.db.session import engine


def run_migration():
    """Add session_documents table for session-document relationship."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = 'session_documents'
        """))

        if result.fetchone() is None:
            # Create the association table
            conn.execute(text("""
                CREATE TABLE session_documents (
                    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    attached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, document_id)
                )
            """))

            # Create indexes for faster lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_session_documents_session_id
                ON session_documents (session_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_session_documents_document_id
                ON session_documents (document_id)
            """))

            conn.commit()
            print("Migration successful: Created session_documents table")
        else:
            print("Migration skipped: session_documents table already exists")


if __name__ == "__main__":
    run_migration()
