Role: You are a Senior AI Engineer and Full-Stack Developer specialized in RAG (Retrieval Augmented Generation).

Project Goal: Build "ResearchRAG," a system designed to help researchers interact with PDF papers efficiently. Core Architecture:

Frontend: Next.js (App Router), TypeScript, Tailwind CSS, Lucide Icons.

Layout: 3-Pane "Holy Grail" Layout.

Left: Chat History / Session Management.

Middle: Current Chat Interface & Summary View.

Right: Evidence Panel (Displays raw text, rendered tables, or images related to the citation).

Backend: FastAPI (Python), LangChain / LangGraph.

Database: PostgreSQL with pgvector extension.

RAG Pipeline:

Parser: Use docling (IBM) for high-fidelity PDF parsing to preserve table structures and identify images.

Chunking Strategy: Parent-Child indexing. We store small "atomic" chunks for search, but retrieve larger "parent" windows for context.

Multimodal: Extracted images from PDFs should be processed (described) by a Vision LLM before embedding.

Database Schema Concept:

documents: Metadata (filename, upload_date).

chunks: content (text), vector (embedding), media_type (text/table/image), parent_id (link to original doc), metadata (page_number, bbox).

chat_sessions: User sessions.

messages: Chat history.

Critical Feature:

"Click-to-Reference": When the LLM generates a response, it must include citation tags (e.g., [source_id]). Clicking this tag in the UI must update the Right Panel to show that specific raw chunk/image.


Phase 1: The Database & Backend Foundation

"Based on the project context, let's start with the Backend and Database.

Set up a FastAPI project structure with SQLAlchemy and Pydantic.

Create the models.py file. I need tables for Document, Chunk (make sure to use pgvector for the embedding column), ChatSession, and Message.

For the Chunk table, add fields for media_type (enum: text, table, image) and raw_metadata (JSON) to store bounding boxes or HTML representation of tables.

Create a database.py connection file using asyncpg.

Generate the code for these files."