"""
RAG Chat Service

Handles vector retrieval and LLM response generation with citations.
"""

import logging
import re
import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Chunk, Document
from app.models.chat import ChatSession, Message, MessageRole
from app.services.ingestion import get_ingestion_service

logger = logging.getLogger(__name__)
settings = get_settings()


# System prompt that enforces citation behavior
SYSTEM_PROMPT = """You are a helpful research assistant that answers questions based on the provided context from academic papers and documents.

IMPORTANT RULES:
1. Answer based ONLY on the provided context. Do not use external knowledge.
2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided documents to answer this question."
3. ALWAYS cite your sources using the format [[chunk_id]] at the end of each sentence that uses information from that source.
4. Be precise and accurate. Quote directly from the context when appropriate.
5. If multiple chunks support a statement, cite all relevant chunks: [[chunk_id_1]][[chunk_id_2]]

Example of proper citation:
"The study found that transformer models outperform RNNs on long sequences [[abc123]]. This is attributed to the self-attention mechanism [[abc123]][[def456]]."

Context from documents:
{context}

Previous conversation:
{chat_history}
"""


class RetrievedChunk:
    """Represents a chunk retrieved from vector search."""

    def __init__(
        self,
        chunk_id: uuid.UUID,
        content: str,
        similarity: float,
        document_id: uuid.UUID,
        document_name: str,
        page_number: Optional[int] = None,
        media_type: str = "text",
    ):
        self.chunk_id = chunk_id
        self.content = content
        self.similarity = similarity
        self.document_id = document_id
        self.document_name = document_name
        self.page_number = page_number
        self.media_type = media_type

    def to_dict(self) -> dict:
        return {
            "chunk_id": str(self.chunk_id),
            "content": self.content,
            "similarity": self.similarity,
            "document_id": str(self.document_id),
            "document_name": self.document_name,
            "page_number": self.page_number,
            "media_type": self.media_type,
        }


class ChatService:
    """Service for RAG-based chat with vector retrieval and LLM generation."""

    def __init__(self):
        self._llm = None
        self._embedding_service = None

    @property
    def embedding_service(self):
        """Get the embedding service (reuse from ingestion)."""
        if self._embedding_service is None:
            ingestion_service = get_ingestion_service()
            self._embedding_service = ingestion_service.embedding_service
        return self._embedding_service

    @property
    def llm(self):
        """Lazy load the LLM."""
        if self._llm is None:
            if settings.openai_api_key and settings.openai_api_key != "sk-your-key-here":
                try:
                    from langchain_openai import ChatOpenAI

                    self._llm = ChatOpenAI(
                        model=settings.chat_model,
                        openai_api_key=settings.openai_api_key,
                        temperature=0.1,  # Low temperature for factual responses
                    )
                    logger.info(f"Using ChatOpenAI with model: {settings.chat_model}")
                except Exception as e:
                    logger.error(f"Failed to initialize ChatOpenAI: {e}")
                    raise RuntimeError("Failed to initialize LLM. Check your OpenAI API key.")
            else:
                raise RuntimeError("OpenAI API key is required for chat functionality.")
        return self._llm

    def retrieve_context(
        self,
        query: str,
        db: Session,
        top_k: int = None,
        document_ids: Optional[list[uuid.UUID]] = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks using cosine similarity search with pgvector.

        Args:
            query: The user's question
            db: Database session
            top_k: Number of chunks to retrieve (defaults to settings.similarity_top_k)
            document_ids: Optional list of document IDs to filter by

        Returns:
            List of RetrievedChunk objects sorted by similarity
        """
        if top_k is None:
            top_k = settings.similarity_top_k

        # Generate embedding for the query
        query_embedding = self.embedding_service.generate_embedding(query)

        # Build the SQL query for cosine similarity search
        # pgvector uses <=> for cosine distance (1 - similarity)
        # We want to order by similarity (descending), so we order by distance (ascending)

        # Format embedding as PostgreSQL array literal
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Base query with cosine similarity
        # Note: We inject the embedding directly to avoid SQLAlchemy param conflicts with ::
        sql = f"""
            SELECT
                c.id as chunk_id,
                c.content,
                c.document_id,
                c.page_number,
                c.media_type,
                d.original_filename as document_name,
                1 - (c.vector <=> '{embedding_str}'::vector) as similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.vector IS NOT NULL
        """

        params = {"top_k": top_k}

        # Add document filter if specified
        if document_ids and len(document_ids) > 0:
            doc_ids_str = ",".join(f"'{str(did)}'" for did in document_ids)
            sql += f" AND c.document_id IN ({doc_ids_str})"

        sql += f"""
            ORDER BY c.vector <=> '{embedding_str}'::vector
            LIMIT :top_k
        """

        try:
            result = db.execute(text(sql), params)
            rows = result.fetchall()

            chunks = []
            for row in rows:
                chunks.append(RetrievedChunk(
                    chunk_id=row.chunk_id,
                    content=row.content,
                    similarity=float(row.similarity) if row.similarity else 0.0,
                    document_id=row.document_id,
                    document_name=row.document_name,
                    page_number=row.page_number,
                    media_type=row.media_type.value if hasattr(row.media_type, 'value') else str(row.media_type),
                ))

            logger.info(f"Retrieved {len(chunks)} chunks for query (top similarity: {chunks[0].similarity:.3f})" if chunks else "No chunks retrieved")
            return chunks

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            raise

    def format_context(self, chunks: list[RetrievedChunk]) -> str:
        """Format retrieved chunks into a context string for the LLM."""
        if not chunks:
            return "No relevant context found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source: {chunk.document_name}"
            if chunk.page_number:
                source_info += f", Page {chunk.page_number}"
            source_info += f", Chunk ID: {chunk.chunk_id}]"

            context_parts.append(f"---\n{source_info}\n{chunk.content}\n")

        return "\n".join(context_parts)

    def format_chat_history(self, messages: list[Message], max_messages: int = 10) -> str:
        """Format recent chat history for context."""
        if not messages:
            return "No previous conversation."

        # Get last N messages (excluding the current user message)
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

        history_parts = []
        for msg in recent_messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            # Truncate long messages in history
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            history_parts.append(f"{role}: {content}")

        return "\n".join(history_parts)

    def extract_citations(self, response_text: str) -> list[uuid.UUID]:
        """Extract chunk IDs from [[chunk_id]] citations in the response."""
        # Pattern to match [[uuid]] citations
        pattern = r'\[\[([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]\]'
        matches = re.findall(pattern, response_text, re.IGNORECASE)

        # Convert to UUIDs and deduplicate while preserving order
        citations = []
        seen = set()
        for match in matches:
            try:
                uid = uuid.UUID(match)
                if uid not in seen:
                    citations.append(uid)
                    seen.add(uid)
            except ValueError:
                continue

        return citations

    async def generate_response(
        self,
        user_query: str,
        chat_history: list[Message],
        retrieved_chunks: list[RetrievedChunk],
    ) -> tuple[str, list[uuid.UUID]]:
        """
        Generate a response using the LLM with retrieved context.

        Args:
            user_query: The user's question
            chat_history: Previous messages in the conversation
            retrieved_chunks: Chunks retrieved from vector search

        Returns:
            Tuple of (response_text, list of cited chunk IDs)
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        # Format context and history
        context = self.format_context(retrieved_chunks)
        history = self.format_chat_history(chat_history)

        # Build the system prompt
        system_content = SYSTEM_PROMPT.format(
            context=context,
            chat_history=history,
        )

        # Create messages for the LLM
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_query),
        ]

        try:
            # Generate response
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Extract citations from the response
            citations = self.extract_citations(response_text)

            # Validate citations against retrieved chunks
            valid_chunk_ids = {chunk.chunk_id for chunk in retrieved_chunks}
            valid_citations = [c for c in citations if c in valid_chunk_ids]

            if len(valid_citations) != len(citations):
                logger.warning(f"Some citations were invalid: {len(citations) - len(valid_citations)} removed")

            logger.info(f"Generated response with {len(valid_citations)} citations")
            return response_text, valid_citations

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    async def chat(
        self,
        session: ChatSession,
        user_message: str,
        db: Session,
    ) -> tuple[Message, list[RetrievedChunk]]:
        """
        Process a chat message: retrieve context, generate response, save to DB.

        Args:
            session: The chat session
            user_message: The user's message content
            db: Database session

        Returns:
            Tuple of (assistant Message, list of retrieved chunks used)
        """
        # Save user message
        user_msg = Message(
            session_id=session.id,
            role=MessageRole.USER,
            content=user_message,
        )
        db.add(user_msg)
        db.commit()

        # Get chat history (excluding the message we just added)
        chat_history = [
            msg for msg in session.messages
            if msg.id != user_msg.id
        ][-10:]  # Last 10 messages for context

        # Retrieve relevant chunks
        retrieved_chunks = self.retrieve_context(
            query=user_message,
            db=db,
            document_ids=session.document_ids if session.document_ids else None,
        )

        # Generate response with citations
        response_text, citations = await self.generate_response(
            user_query=user_message,
            chat_history=chat_history,
            retrieved_chunks=retrieved_chunks,
        )

        # Save assistant message
        assistant_msg = Message(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            citations=citations,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Update session timestamp
        session.updated_at = assistant_msg.created_at
        db.commit()

        return assistant_msg, retrieved_chunks


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create the chat service singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
