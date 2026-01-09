from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.document import MediaType


class ChunkBase(BaseModel):
    content: str
    media_type: MediaType = MediaType.TEXT
    page_number: Optional[int] = None
    bbox: Optional[dict] = None


class ChunkCreate(ChunkBase):
    document_id: UUID
    parent_chunk_id: Optional[UUID] = None


class ChunkResponse(ChunkBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    parent_chunk_id: Optional[UUID] = None
    chunk_index: Optional[int] = None
    created_at: datetime


class DocumentBase(BaseModel):
    filename: str
    original_filename: str


class DocumentCreate(DocumentBase):
    file_path: str
    file_size: Optional[int] = None


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    upload_date: datetime
    processed: Optional[datetime] = None


class DocumentWithChunks(DocumentResponse):
    chunks: list[ChunkResponse] = []
