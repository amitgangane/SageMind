"""
Migration to add file_hash column to documents table.
Run this once to update existing database schema.
"""
from sqlalchemy import text
from app.db.session import engine


def run_migration():
    """Add file_hash column to documents table for deduplication."""
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'documents' AND column_name = 'file_hash'
        """))

        if result.fetchone() is None:
            # Add the column
            conn.execute(text("""
                ALTER TABLE documents
                ADD COLUMN file_hash VARCHAR(64)
            """))

            # Add index for faster duplicate lookups
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_documents_file_hash
                ON documents (file_hash)
            """))

            conn.commit()
            print("Migration successful: Added file_hash column to documents table")
        else:
            print("Migration skipped: file_hash column already exists")


if __name__ == "__main__":
    run_migration()
