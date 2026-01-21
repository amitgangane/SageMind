import uuid
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.models.document import Document, Chunk
from app.schemas.document import DocumentResponse, DocumentWithChunks, ChunkResponse
from app.services.ingestion import get_ingestion_service


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()
logger = logging.getLogger(__name__)


def process_document_task(document_id: uuid.UUID):
    """Background task to process a document."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            ingestion_service = get_ingestion_service()
            ingestion_service.process_document(document, db)
            logger.info(f"Document {document_id} processed successfully")
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    process: bool = True,
):
    """
    Upload a PDF document for processing.

    Args:
        file: The PDF file to upload
        process: If True, automatically process the document after upload (default: True)

    Returns existing document if the same file was already uploaded (based on content hash).
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Create upload directory if needed
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    # Save file to a temporary location first to calculate hash
    file_id = uuid.uuid4()
    filename = f"{file_id}.pdf"
    file_path = upload_path / filename

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Calculate file hash
    file_hash = calculate_file_hash(file_path)

    # Check for existing document with same hash
    existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_doc:
        # Delete the uploaded file since we already have it
        file_path.unlink()
        logger.info(f"Document already exists: {existing_doc.id} (hash: {file_hash[:8]}...)")
        return existing_doc

    # Get file size
    file_size = file_path.stat().st_size

    # Create document record
    document = Document(
        id=file_id,
        filename=filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_hash=file_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Process the document (parse, chunk, embed)
    if process:
        if background_tasks:
            # Process in background for better response time
            background_tasks.add_task(process_document_task, document.id)
        else:
            # Process synchronously
            try:
                ingestion_service = get_ingestion_service()
                document = ingestion_service.process_document(document, db)
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                # Document is saved but not processed - can retry later
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Document uploaded but processing failed: {str(e)}",
                )

    return document


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all uploaded documents."""
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents


@router.get("/{document_id}", response_model=DocumentWithChunks)
async def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get document details with all chunks."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Delete a document and all its chunks."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete file from disk
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(document)
    db.commit()


@router.get("/{document_id}/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    document_id: uuid.UUID,
    chunk_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a specific chunk by ID (for click-to-reference feature)."""
    chunk = db.query(Chunk).filter(
        Chunk.id == chunk_id,
        Chunk.document_id == document_id,
    ).first()
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
    return chunk


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Manually trigger processing for a document.
    Useful for reprocessing or if initial processing failed.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete existing chunks if reprocessing
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.commit()

    try:
        ingestion_service = get_ingestion_service()
        document = ingestion_service.process_document(document, db)
        return document
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )
