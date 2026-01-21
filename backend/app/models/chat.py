import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Association table for Many-to-Many relationship between ChatSession and Document
session_documents = Table(
    "session_documents",
    Base.metadata,
    Column("session_id", UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("attached_at", DateTime, default=datetime.utcnow),
)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_ = Column("metadata", JSONB, default=dict)

    # Legacy field - kept for backward compatibility, will be migrated to relationship
    document_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)

    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")
    documents = relationship("Document", secondary=session_documents, backref="sessions")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Store citation references: list of chunk IDs referenced in this message
    citations = Column(ARRAY(UUID(as_uuid=True)), default=list)
    metadata_ = Column("metadata", JSONB, default=dict)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
