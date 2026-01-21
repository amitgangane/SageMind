from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageRole


class MessageBase(BaseModel):
    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    session_id: UUID


class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    created_at: datetime
    citations: list[UUID] = []


class DocumentBrief(BaseModel):
    """Lightweight document info for session attachments."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None


class ChatSessionBase(BaseModel):
    title: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    document_ids: list[UUID] = []


class ChatSessionResponse(ChatSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    document_ids: list[UUID] = []  # Legacy field
    attached_documents: list[DocumentBrief] = []  # Full document relationship


class ChatSessionWithMessages(ChatSessionResponse):
    messages: list[MessageResponse] = []


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str
    session_id: Optional[UUID] = None
    # Documents to attach to the session (for new sessions or adding more docs)
    attach_document_ids: list[UUID] = Field(default_factory=list)
    # Filter to search only within a specific document (for @ tagging)
    filter_document_id: Optional[UUID] = None


class SourceChunk(BaseModel):
    """A source chunk used in generating the response."""
    chunk_id: str
    content: str
    similarity: float
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    media_type: str = "text"
    image_url: Optional[str] = None  # URL to image file (e.g., /static/images/...)
    caption: Optional[str] = None  # Image caption if available


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    session_id: UUID
    message: MessageResponse
    citations: list[UUID] = []
    sources: list[SourceChunk] = []  # The chunks used to generate the response
