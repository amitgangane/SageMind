import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum

from app.db.base import Base
from app.core.config import get_settings

settings = get_settings()


class MediaType(str, enum.Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)

    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    vector = Column(Vector(settings.embedding_dimension), nullable=True)
    media_type = Column(SQLEnum(MediaType), default=MediaType.TEXT)

    # Parent-child chunking: parent_chunk_id links small chunks to larger context chunks
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)

    # Metadata for source tracking
    page_number = Column(Integer, nullable=True)
    bbox = Column(JSONB, nullable=True)  # Bounding box: {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
    chunk_index = Column(Integer, nullable=True)  # Order within document
    metadata_ = Column("metadata", JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    parent_chunk = relationship("Chunk", remote_side=[id], backref="child_chunks")
