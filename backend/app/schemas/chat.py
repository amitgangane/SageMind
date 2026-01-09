from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

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


class ChatSessionBase(BaseModel):
    title: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    document_ids: list[UUID] = []


class ChatSessionResponse(ChatSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    document_ids: list[UUID] = []


class ChatSessionWithMessages(ChatSessionResponse):
    messages: list[MessageResponse] = []


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str
    session_id: Optional[UUID] = None
    document_ids: list[UUID] = []


class SourceChunk(BaseModel):
    """A source chunk used in generating the response."""
    chunk_id: str
    content: str
    similarity: float
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    media_type: str = "text"


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    session_id: UUID
    message: MessageResponse
    citations: list[UUID] = []
    sources: list[SourceChunk] = []  # The chunks used to generate the response
