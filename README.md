# Semantic FS

**AI-Driven File Management System** — Search, explore, and manage your files using natural language.

---

## Overview

Semantic FS is a full-stack application that brings semantic search capabilities to file management. Instead of searching by filename, you can describe what you're looking for in plain language, and the system understands the *content* of your files.

**Core Features:**
- **Semantic Search** — Find files by describing their content, not just their names
- **Cloud Storage Integration** — Connect to Google Drive for seamless file access
- **Multi-format Support** — Works with PDFs, DOCX, text files, and more
- **RAG-Powered Responses** — Get AI-generated answers based on your file contents
- **Real-time Indexing** — Kafka-based event system keeps the search index up-to-date

---

## For Users

### Getting Started

1. **Sign In**
   - Click "Sign in with Google" to connect your Google Drive
   - Guest mode available for exploration without authentication

2. **Search Files**
   - Use the search bar to describe what you're looking for
   - Example: "quarterly financial report from last year" instead of "Q4_finance.pdf"

### Requirements

- Python 3.11+
- Node.js 18+
- Google Cloud project with Drive API enabled
- PostgreSQL with pgvector extension
- Kafka (or Docker for containerized setup)

---

## For Developers

### Architecture Overview

```
src/
├── llm/              # LLM integration (RAG, semantic analysis, agent research)
├── vector_db/        # Vector storage (Qdrant) and embedding management
├── file_ops/         # File operations and cloud storage adapters
├── gateway_auth/     # Authentication gateway (OAuth 2.0)
├── kafka/            # Event streaming for real-time indexing
└── event_db/         # Event store for file change tracking

ui/
├── js/               # Vanilla JS frontend with modular components
└── css/              # Styled CSS with theme support
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| LLM Service | 8001 | AI responses, RAG search, agent research |
| File Ops | 8002 | File operations, cloud storage |
| Vector DB | 8003 | Embedding storage and similarity search |
| UI | 5500 | Web interface |

### Running Locally

```bash
# 1. Set up virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment variables
cp src/llm/.env.example src/llm/.env  # Configure API keys
cp src/file_ops/.env.example src/file_ops/.env

# 3. Start backend services
uvicorn src.llm.endpoints.main:app --port 8001 --reload &
uvicorn src.file_ops.endpoints.main:app --port 8002 --reload &

# 4. Start frontend
cd ui && npm install && npm run dev
```

### Key Dependencies

- **FastAPI** — Web framework for REST endpoints
- **Qdrant/pgvector** — Vector similarity search
- **Kafka** — Event streaming for real-time updates
- **LangChain** — LLM orchestration and RAG pipelines
- **Google API Client** — Google Drive integration

---

## For AI Engineers

### Technical Deep Dive

#### Vector Storage Pipeline

```
User Query → OpenAI Embeddings → Vector Search (Qdrant) → Top-K Results → LLM Context
```

The system uses OpenAI's `text-embedding-3-small` model for generating embeddings stored in Qdrant. Query similarity search retrieves the most relevant file chunks for RAG context.

#### RAG Architecture

1. **Indexing Flow**
   ```
   File Upload → Text Extraction → Chunking → Embedding → Vector DB
                              ↓
                          Kafka Event → Event Store
   ```

2. **Query Flow**
   ```
   Natural Language Query → Embedding → Vector Search → Context Assembly → LLM Response
   ```

#### Adapter Pattern

Each domain uses the adapter pattern for flexibility:

```
domain/          → Interfaces and business logic (pure Python)
adapters/        → Concrete implementations (Qdrant, OpenAI, Google Drive)
```

This allows swapping LLM providers, vector databases, or storage backends without changing core logic.

#### Event-Driven Indexing

File changes trigger Kafka events that update the vector index asynchronously. This ensures:
- Non-blocking file operations
- eventual consistency for search results
- Decoupled architecture between services

### Environment Variables

```bash
# LLM Service
OPENAI_API_KEY=sk-...

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=semantic_fs

# File Ops
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8002/auth/callback

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/semantic_fs
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```
