import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.chat import ChatSession, Message, MessageRole
from app.models.document import Document
from app.schemas.chat import (
    ChatSessionResponse,
    ChatSessionCreate,
    ChatSessionWithMessages,
    MessageResponse,
    ChatRequest,
    ChatResponse,
    SourceChunk,
    DocumentBrief,
)
from app.services.chat import get_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def session_to_response(session: ChatSession) -> dict:
    """Convert session model to response dict with attached documents."""
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "document_ids": session.document_ids or [],
        "attached_documents": [
            DocumentBrief(
                id=doc.id,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                page_count=doc.page_count,
            )
            for doc in session.documents
        ],
    }


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new chat session with optional document attachments."""
    session = ChatSession(
        title=session_data.title,
        document_ids=session_data.document_ids,  # Legacy
    )

    # Attach documents using many-to-many relationship
    if session_data.document_ids:
        documents = db.query(Document).filter(Document.id.in_(session_data.document_ids)).all()
        session.documents = documents

    db.add(session)
    db.commit()
    db.refresh(session)
    return session_to_response(session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all chat sessions with their attached documents."""
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
    return [session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a chat session with all messages and attached documents."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    response = session_to_response(session)
    response["messages"] = [MessageResponse.model_validate(m) for m in session.messages]
    return response


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


@router.post("/sessions/{session_id}/documents/{document_id}", response_model=ChatSessionResponse)
async def attach_document_to_session(
    session_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Attach a document to an existing session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document not in session.documents:
        session.documents.append(document)
        db.commit()
        db.refresh(session)

    return session_to_response(session)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message and get a RAG-powered response.

    - If session_id is not provided, creates a new session.
    - Uses documents attached to the session for retrieval context.
    - If attach_document_ids is provided, attaches those documents to the session.
    - If filter_document_id is provided (@ tagging), searches only that document.
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
        # Create new session
        session = ChatSession(
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Attach new documents to session if provided
    if request.attach_document_ids:
        documents = db.query(Document).filter(Document.id.in_(request.attach_document_ids)).all()
        for doc in documents:
            if doc not in session.documents:
                session.documents.append(doc)
        db.commit()
        db.refresh(session)

    # Determine which documents to search
    # Priority: filter_document_id > session.documents > all documents
    if request.filter_document_id:
        # @ tagging - search only the specified document
        search_document_ids = [request.filter_document_id]
    elif session.documents:
        # Use session's attached documents
        search_document_ids = [doc.id for doc in session.documents]
    else:
        # No documents attached - search all (or could return error)
        search_document_ids = None

    try:
        # Get the chat service and process the message
        chat_service = get_chat_service()
        assistant_message, retrieved_chunks = await chat_service.chat(
            session=session,
            user_message=request.message,
            db=db,
            document_ids=search_document_ids,
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
                image_url=chunk.image_url,
                caption=chunk.caption,
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

    # Get image info from metadata if this is an image chunk
    image_url = None
    caption = None
    if chunk.media_type.value == "image" and chunk.metadata_:
        image_url = chunk.metadata_.get("image_url")
        caption = chunk.metadata_.get("caption")

    return {
        "chunk_id": str(chunk.id),
        "content": chunk.content,
        "media_type": chunk.media_type.value,
        "page_number": chunk.page_number,
        "bbox": chunk.bbox,
        "image_url": image_url,
        "caption": caption,
        "document": {
            "id": str(document.id),
            "filename": document.original_filename,
        } if document else None,
    }
