"""
Ingestion Pipeline Service

Handles PDF parsing, chunking, embedding generation, and database storage.
"""

import base64
import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import random
import io

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, Chunk, MediaType

logger = logging.getLogger(__name__)
settings = get_settings()

# Static directory for images
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
IMAGES_DIR = STATIC_DIR / "images"


class EmbeddingService:
    """Handles embedding generation with OpenAI or mock fallback."""

    def __init__(self):
        self.dimension = settings.embedding_dimension
        self._embeddings_model = None

    @property
    def embeddings_model(self):
        """Lazy load the embeddings model."""
        if self._embeddings_model is None:
            if settings.openai_api_key and settings.openai_api_key != "sk-your-key-here":
                try:
                    from langchain_openai import OpenAIEmbeddings

                    self._embeddings_model = OpenAIEmbeddings(
                        model=settings.embedding_model,
                        openai_api_key=settings.openai_api_key,
                    )
                    logger.info("Using OpenAI embeddings")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI embeddings: {e}")
                    self._embeddings_model = "mock"
            else:
                logger.info("No OpenAI API key provided, using mock embeddings")
                self._embeddings_model = "mock"
        return self._embeddings_model

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if self.embeddings_model == "mock":
            return self._mock_embedding(text)

        try:
            embedding = self.embeddings_model.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return self._mock_embedding(text)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if self.embeddings_model == "mock":
            return [self._mock_embedding(t) for t in texts]

        try:
            embeddings = self.embeddings_model.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return [self._mock_embedding(t) for t in texts]

    def _mock_embedding(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding based on text hash."""
        # Use hash for deterministic but varied vectors
        text_hash = hashlib.md5(text.encode()).hexdigest()
        random.seed(int(text_hash, 16) % (2**32))
        return [random.uniform(-1, 1) for _ in range(self.dimension)]


class TextChunker:
    """Splits text into semantic chunks of approximately 300-500 tokens."""

    def __init__(self, target_tokens: int = 400, overlap_tokens: int = 50):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        # Approximate: 1 token ≈ 4 characters for English text
        self.chars_per_token = 4

    def chunk_text(self, text: str) -> list[dict]:
        """
        Split text into chunks, trying to respect sentence boundaries.
        Returns list of dicts with 'content' and 'char_start' keys.
        """
        if not text or not text.strip():
            return []

        target_chars = self.target_tokens * self.chars_per_token
        overlap_chars = self.overlap_tokens * self.chars_per_token

        # Split into sentences (simple approach)
        sentences = self._split_into_sentences(text)

        chunks = []
        current_chunk = []
        current_length = 0
        chunk_start = 0
        char_position = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds target, save current chunk
            if current_length + sentence_length > target_chars and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "content": chunk_text.strip(),
                    "char_start": chunk_start,
                })

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap_chars)
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text) if overlap_text else 0
                chunk_start = char_position - len(overlap_text) if overlap_text else char_position

            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
            char_position += sentence_length + 1

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if chunk_text.strip():
                chunks.append({
                    "content": chunk_text.strip(),
                    "char_start": chunk_start,
                })

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re

        # Simple sentence splitting - handles . ! ? followed by space and capital
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        # Also split on double newlines (paragraph breaks)
        result = []
        for s in sentences:
            paragraphs = s.split('\n\n')
            result.extend([p.strip() for p in paragraphs if p.strip()])
        return result

    def _get_overlap_text(self, chunks: list[str], max_chars: int) -> str:
        """Get the last N characters worth of text for overlap."""
        combined = " ".join(chunks)
        if len(combined) <= max_chars:
            return combined
        return combined[-max_chars:]


class PDFProcessor:
    """Handles PDF parsing using docling."""

    def __init__(self):
        self._converter = None

    @property
    def converter(self):
        """Lazy load the docling converter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter

                self._converter = DocumentConverter()
                logger.info("Docling converter initialized")
            except ImportError as e:
                logger.error(f"Failed to import docling: {e}")
                raise ImportError(
                    "docling is required for PDF processing. "
                    "Install it with: pip install docling"
                )
        return self._converter

    def process_pdf(self, file_path: str, doc_id: str = None) -> dict:
        """
        Process a PDF file and extract text, tables, and images.

        Args:
            file_path: Path to the PDF file
            doc_id: Document ID for naming image files

        Returns:
            dict with keys:
                - text_chunks: list of text chunk dicts
                - tables: list of table dicts (markdown format)
                - images: list of image dicts with image_url
                - page_count: number of pages
                - metadata: document metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Processing PDF: {file_path}")

        # Convert PDF using docling
        result = self.converter.convert(str(file_path))
        doc = result.document

        # Extract components
        text_content = self._extract_text(doc)
        tables = self._extract_tables(doc)
        images = self._extract_images(doc, file_path, doc_id=doc_id)

        # Get page count
        page_count = self._get_page_count(doc)

        # Chunk the text
        chunker = TextChunker()
        text_chunks = chunker.chunk_text(text_content)

        return {
            "text_chunks": text_chunks,
            "tables": tables,
            "images": images,
            "page_count": page_count,
            "metadata": {
                "source": str(file_path),
                "processed_at": datetime.utcnow().isoformat(),
            },
        }

    def _extract_text(self, doc) -> str:
        """Extract all text content from the document."""
        try:
            # Docling provides markdown export which preserves structure
            text = doc.export_to_markdown()
            return text
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
            return ""

    def _extract_tables(self, doc) -> list[dict]:
        """Extract tables and convert to markdown format."""
        tables = []
        try:
            # Iterate through document items to find tables
            for item_ix, item in enumerate(doc.iterate_items()):
                element = item[1] if isinstance(item, tuple) else item

                # Check if this is a table
                if hasattr(element, 'export_to_markdown'):
                    # Try to identify tables by their type
                    element_type = type(element).__name__
                    if 'Table' in element_type:
                        try:
                            table_md = element.export_to_markdown()
                            if table_md and '|' in table_md:  # Basic check for markdown table
                                # Try to get page number
                                page_num = None
                                if hasattr(element, 'prov') and element.prov:
                                    for prov in element.prov:
                                        if hasattr(prov, 'page_no'):
                                            page_num = prov.page_no
                                            break

                                tables.append({
                                    "content": table_md,
                                    "page_number": page_num,
                                    "index": len(tables),
                                })
                        except Exception as e:
                            logger.debug(f"Error exporting table: {e}")

        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")

        logger.info(f"Extracted {len(tables)} tables")
        return tables

    def _extract_images(self, doc, file_path: Path, doc_id: str = None) -> list[dict]:
        """Extract images from the document and save to static files."""
        images = []

        # Ensure images directory exists
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        try:
            # Iterate through document items to find pictures/figures
            for item_ix, item in enumerate(doc.iterate_items()):
                element = item[1] if isinstance(item, tuple) else item
                element_type = type(element).__name__

                if 'Picture' in element_type or 'Figure' in element_type:
                    try:
                        page_num = None
                        bbox = None
                        caption = None
                        image_url = None

                        # Get provenance info (page number, bounding box)
                        if hasattr(element, 'prov') and element.prov:
                            for prov in element.prov:
                                if hasattr(prov, 'page_no'):
                                    page_num = prov.page_no
                                if hasattr(prov, 'bbox'):
                                    bbox = {
                                        "x1": prov.bbox.l,
                                        "y1": prov.bbox.t,
                                        "x2": prov.bbox.r,
                                        "y2": prov.bbox.b,
                                    } if hasattr(prov.bbox, 'l') else None
                                break

                        # Try to get caption
                        if hasattr(element, 'caption') and element.caption:
                            caption = str(element.caption)
                        elif hasattr(element, 'text') and element.text:
                            caption = str(element.text)

                        # Try to get image content and save to file
                        if hasattr(element, 'image') and element.image:
                            if hasattr(element.image, 'pil_image') and element.image.pil_image:
                                img = element.image.pil_image

                                # Generate filename
                                image_index = len(images)
                                filename = f"{doc_id}_fig_{image_index}.png"
                                image_path = IMAGES_DIR / filename

                                # Save image to file
                                img.save(str(image_path), format='PNG')
                                image_url = f"/static/images/{filename}"

                                logger.info(f"Saved image to {image_path}")

                        # Store image info
                        images.append({
                            "image_url": image_url,
                            "caption": caption,
                            "page_number": page_num,
                            "bbox": bbox,
                            "index": len(images),
                            "has_image": image_url is not None,
                        })

                    except Exception as e:
                        logger.debug(f"Error extracting image: {e}")

        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        logger.info(f"Extracted {len(images)} images")
        return images

    def _get_page_count(self, doc) -> int:
        """Get the total number of pages in the document."""
        try:
            if hasattr(doc, 'pages'):
                return len(doc.pages)
            # Try to infer from provenance
            max_page = 0
            for item in doc.iterate_items():
                element = item[1] if isinstance(item, tuple) else item
                if hasattr(element, 'prov') and element.prov:
                    for prov in element.prov:
                        if hasattr(prov, 'page_no') and prov.page_no:
                            max_page = max(max_page, prov.page_no)
            return max_page if max_page > 0 else 1
        except Exception:
            return 1


class IngestionService:
    """Main service for document ingestion pipeline."""

    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.embedding_service = EmbeddingService()

    def process_document(self, document: Document, db: Session) -> Document:
        """
        Process an uploaded document: parse, chunk, embed, and store.

        Args:
            document: The Document model instance
            db: Database session

        Returns:
            Updated Document with processed timestamp and chunks
        """
        logger.info(f"Starting ingestion for document: {document.id}")

        try:
            # Parse the PDF (pass doc_id for naming image files)
            parsed = self.pdf_processor.process_pdf(
                document.file_path,
                doc_id=str(document.id)
            )

            # Update document metadata
            document.page_count = parsed["page_count"]
            document.metadata_ = parsed["metadata"]

            # Collect all chunks to process
            all_chunks = []
            chunk_index = 0

            # Process text chunks
            for text_chunk in parsed["text_chunks"]:
                all_chunks.append({
                    "content": text_chunk["content"],
                    "media_type": MediaType.TEXT,
                    "page_number": None,  # Could be inferred from char_start
                    "bbox": None,
                    "chunk_index": chunk_index,
                    "metadata": {"char_start": text_chunk.get("char_start")},
                })
                chunk_index += 1

            # Process tables
            for table in parsed["tables"]:
                all_chunks.append({
                    "content": table["content"],
                    "media_type": MediaType.TABLE,
                    "page_number": table.get("page_number"),
                    "bbox": None,
                    "chunk_index": chunk_index,
                    "metadata": {
                        "table_index": table.get("index"),
                    },
                })
                chunk_index += 1

            # Process images with saved file URLs
            for image in parsed["images"]:
                page_num = image.get('page_number', 'unknown')
                image_index = image.get("index", 0) + 1
                caption = image.get("caption") or ""

                # Create searchable content - use caption if available
                if caption:
                    content = f"[Figure {image_index} on page {page_num}]: {caption}"
                else:
                    content = (
                        f"[Figure {image_index}: Image, diagram, or figure on page {page_num}. "
                        f"This visual element may contain charts, graphs, architecture diagrams, "
                        f"flowcharts, illustrations, or other visual content.]"
                    )

                all_chunks.append({
                    "content": content,
                    "media_type": MediaType.IMAGE,
                    "page_number": image.get("page_number"),
                    "bbox": image.get("bbox"),
                    "chunk_index": chunk_index,
                    "metadata": {
                        "image_index": image.get("index"),
                        "image_url": image.get("image_url"),  # URL to static file
                        "caption": caption,
                        "has_image": image.get("has_image", False),
                    },
                })
                chunk_index += 1

            # Generate embeddings for all chunks
            logger.info(f"Generating embeddings for {len(all_chunks)} chunks")
            contents = [c["content"] for c in all_chunks]
            embeddings = self.embedding_service.generate_embeddings(contents)

            # Create chunk records
            for i, chunk_data in enumerate(all_chunks):
                chunk = Chunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    content=chunk_data["content"],
                    vector=embeddings[i],
                    media_type=chunk_data["media_type"],
                    page_number=chunk_data["page_number"],
                    bbox=chunk_data["bbox"],
                    chunk_index=chunk_data["chunk_index"],
                    metadata_=chunk_data["metadata"],
                )
                db.add(chunk)

            # Mark document as processed
            document.processed = datetime.utcnow()
            db.commit()
            db.refresh(document)

            logger.info(
                f"Document {document.id} processed successfully: "
                f"{len(parsed['text_chunks'])} text chunks, "
                f"{len(parsed['tables'])} tables, "
                f"{len(parsed['images'])} images"
            )

            return document

        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            db.rollback()
            raise


# Singleton instance
_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Get or create the ingestion service singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
