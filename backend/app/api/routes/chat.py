import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.chat import ChatSession, Message, MessageRole
from app.schemas.chat import (
    ChatSessionResponse,
    ChatSessionCreate,
    ChatSessionWithMessages,
    MessageResponse,
    ChatRequest,
    ChatResponse,
    SourceChunk,
)
from app.services.chat import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        title=session_data.title,
        document_ids=session_data.document_ids,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all chat sessions."""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a chat session with all messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    db.delete(session)
    db.commit()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message and get a RAG-powered response.

    If session_id is not provided, creates a new session.
    Returns the AI response with citations and source chunks.
    """
    # Get or create session
    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        session = ChatSession(
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            document_ids=request.document_ids,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    try:
        # Get the chat service and process the message
        chat_service = get_chat_service()
        assistant_message, retrieved_chunks = await chat_service.chat(
            session=session,
            user_message=request.message,
            db=db,
        )

        # Convert retrieved chunks to response format
        sources = [
            SourceChunk(
                chunk_id=str(chunk.chunk_id),
                content=chunk.content,
                similarity=chunk.similarity,
                document_id=str(chunk.document_id),
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                media_type=chunk.media_type,
            )
            for chunk in retrieved_chunks
        ]

        return ChatResponse(
            session_id=session.id,
            message=MessageResponse.model_validate(assistant_message),
            citations=assistant_message.citations or [],
            sources=sources,
        )

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}",
        )


@router.get("/chunks/{chunk_id}", response_model=dict)
async def get_chunk_for_citation(
    chunk_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get chunk details for the click-to-reference feature.
    Returns chunk content with document context.
    """
    from app.models.document import Chunk, Document

    chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )

    document = db.query(Document).filter(Document.id == chunk.document_id).first()

    return {
        "chunk_id": str(chunk.id),
        "content": chunk.content,
        "media_type": chunk.media_type.value,
        "page_number": chunk.page_number,
        "bbox": chunk.bbox,
        "document": {
            "id": str(document.id),
            "filename": document.original_filename,
        } if document else None,
    }
