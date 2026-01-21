# ResearchRAG (SageMind)

A Retrieval Augmented Generation (RAG) system designed to help researchers interact with PDF papers efficiently. Upload documents, chat with an AI assistant, and get responses with clickable citations that link directly to source material.

## Features

- **PDF Document Ingestion** - Upload PDFs with automatic text, table, and image extraction
- **Intelligent Chunking** - Smart text splitting that respects sentence boundaries with overlap for context
- **Multimodal Support** - Handles text, tables (markdown), and images from documents
- **Semantic Search** - Vector-based retrieval using pgvector for accurate context matching
- **Citation System** - AI responses include clickable citations linking to exact source chunks
- **Session Management** - Organize conversations with document attachments
- **Document Filtering** - Use @ tagging to search within specific documents
- **File Deduplication** - SHA-256 hashing prevents duplicate uploads
- **Click-to-Reference** - View source content in a dedicated panel when clicking citations

## Tech Stack

### Frontend
- **Next.js 16** with App Router
- **TypeScript 5**
- **Tailwind CSS 4**
- **Zustand** for state management
- **react-markdown** with remark-gfm for rendering
- **react-resizable-panels** for the 3-pane layout

### Backend
- **FastAPI** (Python 3.14+)
- **SQLAlchemy 2.0** with asyncpg
- **PostgreSQL** with **pgvector** extension
- **Pydantic** for validation

### AI/ML
- **OpenAI GPT-4o** for chat and vision
- **text-embedding-3-small** for embeddings (1536 dimensions)
- **LangChain** & **LangGraph** for orchestration

### PDF Processing
- **docling** (IBM) - Preserves tables, extracts images with bounding boxes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
├──────────────┬────────────────────────────┬─────────────────────┤
│  Sidebar     │      Chat Interface        │    Source Panel     │
│  (280px)     │         (Flex)             │      (400px)        │
│              │                            │                     │
│ - Sessions   │  - Message Display         │ - Citation Content  │
│ - Documents  │  - Markdown Rendering      │ - Tables/Images     │
│ - Upload     │  - Citation Buttons        │ - Document Info     │
└──────────────┴────────────────────────────┴─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  /api/v1/documents/*     │     /api/v1/chat/*                   │
│  - Upload & Process      │     - Sessions & Messages            │
│  - List & Delete         │     - RAG Retrieval                  │
│  - Chunk Management      │     - Citation Tracking              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                        │
├─────────────────────────────────────────────────────────────────┤
│  documents │ chunks (with vectors) │ chat_sessions │ messages   │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.14+
- Node.js 19+
- PostgreSQL 12+ with pgvector extension
- OpenAI API key

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Research Agent"
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Or create manually
```

Configure your `.env` file:

```env
APP_NAME=ResearchRAG
DEBUG=true
DATABASE_URL=postgresql://user:password@localhost:5432/researchrag
OPENAI_API_KEY=sk-your-api-key
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o
VISION_MODEL=gpt-4o
EMBEDDING_DIMENSION=1536
SIMILARITY_TOP_K=5
UPLOAD_DIR=./uploads
```

Start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Database Setup

Ensure PostgreSQL has the pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The application will automatically create tables on startup.

## Project Structure

```
Research Agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── core/
│   │   │   └── config.py        # Configuration settings
│   │   ├── db/
│   │   │   ├── base.py          # SQLAlchemy Base
│   │   │   ├── session.py       # Database session
│   │   │   └── init_db.py       # Database initialization
│   │   ├── models/
│   │   │   ├── document.py      # Document, Chunk models
│   │   │   └── chat.py          # ChatSession, Message models
│   │   ├── schemas/
│   │   │   ├── document.py      # Response schemas
│   │   │   └── chat.py          # Chat schemas
│   │   ├── services/
│   │   │   ├── ingestion.py     # PDF processing & embedding
│   │   │   └── chat.py          # RAG retrieval & LLM
│   │   └── api/
│   │       └── routes/
│   │           ├── documents.py # Document endpoints
│   │           └── chat.py      # Chat endpoints
│   ├── migrations/              # Database migrations
│   ├── static/images/           # Extracted PDF images
│   ├── uploads/                 # Uploaded PDF files
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx       # Root layout
│   │   │   └── page.tsx         # Home page
│   │   ├── components/
│   │   │   ├── ResearchLayout.tsx
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── SidebarPanel.tsx
│   │   │   └── SourcePanel.tsx
│   │   ├── store/
│   │   │   └── useResearchStore.ts
│   │   ├── lib/
│   │   │   └── api.ts           # API client
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── tailwind.config.ts
│
├── Project_approach.md          # Design specification
└── README.md
```

## API Endpoints

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload and process PDF |
| GET | `/api/v1/documents/` | List all documents |
| GET | `/api/v1/documents/{id}` | Get document with chunks |
| GET | `/api/v1/documents/{id}/chunks/{chunk_id}` | Get specific chunk |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/documents/{id}/process` | Reprocess document |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/sessions` | Create new session |
| GET | `/api/v1/chat/sessions` | List all sessions |
| GET | `/api/v1/chat/sessions/{id}` | Get session with messages |
| DELETE | `/api/v1/chat/sessions/{id}` | Delete session |
| POST | `/api/v1/chat/sessions/{id}/documents/{doc_id}` | Attach document to session |
| POST | `/api/v1/chat/message` | Send message and get RAG response |
| GET | `/api/v1/chat/chunks/{chunk_id}` | Get chunk for citation |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Usage

1. **Upload Documents** - Use the sidebar to upload PDF research papers
2. **Start a Session** - Create a new chat session or continue an existing one
3. **Attach Documents** - Link documents to your session for context
4. **Ask Questions** - Chat naturally about your documents
5. **View Citations** - Click numbered citations to see source content in the right panel
6. **Filter by Document** - Use @ tagging to search within specific documents

## How RAG Works

1. **Ingestion**: PDFs are parsed using docling, extracting text, tables, and images
2. **Chunking**: Content is split into ~300-500 token chunks with overlap
3. **Embedding**: Each chunk is embedded using OpenAI's text-embedding-3-small
4. **Storage**: Chunks and vectors are stored in PostgreSQL with pgvector
5. **Retrieval**: User queries are embedded and matched against chunks via cosine similarity
6. **Generation**: GPT-4o generates responses using retrieved context with citation markers
7. **Citation**: Citations are extracted, validated, and rendered as clickable buttons

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `EMBEDDING_MODEL` | text-embedding-3-small | Embedding model |
| `CHAT_MODEL` | gpt-4o | Chat completion model |
| `VISION_MODEL` | gpt-4o | Vision model for images |
| `EMBEDDING_DIMENSION` | 1536 | Vector dimension |
| `SIMILARITY_TOP_K` | 5 | Number of chunks to retrieve |
| `UPLOAD_DIR` | ./uploads | PDF storage directory |

## Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Database Migrations

Migration scripts are in `backend/migrations/`:

```bash
python -m migrations.add_file_hash
python -m migrations.add_session_documents
```

## License

MIT
