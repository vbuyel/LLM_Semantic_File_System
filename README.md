# Semantic FS

**AI-Driven File Management System** — Search, explore, and manage your files using natural language.

---

## Overview

Semantic FS is a microservices-based application that brings semantic search capabilities to file management. Instead of searching by filename, users can describe what they're looking for in plain language, and the system understands the *content* of their files through AI-powered embeddings.

**Core Features:**
- **Semantic Search** — Find files by describing their content, not just their names
- **Cloud Storage Integration** — Connect to Google Drive and Google Cloud Storage (GCS)
- **Multi-format Support** — Works with PDFs, DOCX, Pages, text files, and more
- **RAG-Powered Responses** — Get AI-generated answers based on your file contents
- **Real-time Indexing** — Kafka-based event system keeps the search index up-to-date
- **User Activity Tracking** — Complete event history for all file operations

---

## Architecture

### Microservices

```
src/
├── llm/              # LLM integration (RAG, semantic analysis, agent research)
├── vector_db/        # Vector storage (PostgreSQL + pgvector) and embedding management
├── file_ops/         # File operations and cloud storage adapters (GCS, Google Drive)
├── gateway_auth/     # Authentication gateway (OAuth 2.0) and API proxy
├── kafka/            # Kafka broker management
└── event_db/         # Event store (PostgreSQL) for file change tracking

ui/
├── js/               # Vanilla JS frontend with modular components
└── css/              # Styled CSS with theme support
```

### Data Flow

```
User Action (Upload/Delete/Rename)
         ↓
    Gateway (port 8000)
         ↓
    File Ops (port 8002) ←→ Cloud Storage (GCS/Google Drive)
         ↓
    Kafka (topics: send_event, request_from_gcs, request_from_gd)
    ┌────┴────┐
    ↓         ↓
Event DB   Vector DB
(port 8003)(chunking + embeddings)
    ↓
Gateway WebSocket → Real-time UI updates
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | FastAPI | REST API endpoints |
| **Vector Database** | PostgreSQL + pgvector | Semantic similarity search |
| **Event Streaming** | Apache Kafka | Asynchronous file processing |
| **LLM Integration** | OpenAI / OpenRouter | AI responses and embeddings |
| **Cloud Storage** | Google Drive API, GCS | File storage backends |
| **Frontend** | Vanilla JS, Vite | User interface |
| **Testing** | pytest, TestClient | Unit, integration, system, acceptance tests |

---

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Gateway | 8000 | API Gateway, OAuth, proxy to other services |
| LLM Service | 8001 | AI responses, RAG search, agent research |
| File Ops | 8002 | File operations, cloud storage |
| Vector DB | 8003 | Embedding storage and similarity search |
| Event DB | 8003 | Event store and WebSocket for real-time updates |
| UI | 5500 | Web interface (Vite dev server) |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Kafka and PostgreSQL)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd LLM_Semantic_File_System

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Each service has its own `.env` file:

```bash
# Vector DB (src/vector_db/.env)
DOCS_POSTGRESQL_USERNAME=postgres
DOCS_POSTGRESQL_PASSWORD=your_password
DOCS_POSTGRESQL_HOST=localhost
DOCS_POSTGRESQL_PORT=5432
DOCS_POSTGRESQL_DB=vector_db
BROKER_HOSTS=localhost:9092

# Event DB (src/event_db/.env)
EVENT_POSTGRESQL_USERNAME=postgres
EVENT_POSTGRESQL_PASSWORD=your_password
EVENT_POSTGRESQL_HOST=localhost
EVENT_POSTGRESQL_PORT=5432
EVENT_POSTGRESQL_DB=events_db

# File Ops (src/file_ops/.env)
GCS_BUCKET_NAME=your_bucket
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# LLM Service (src/llm/.env)
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-...
```

### 3. Start Infrastructure (Docker)

```bash
# PostgreSQL with pgvector
docker run -d --name semantic-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=vector_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Kafka
cd src/kafka && docker-compose up -d
```

### 4. Start Services

```bash
# Terminal 1: Event DB (port 8003)
python -m src.event_db.kafka_conn.main

# Terminal 2: Vector DB (background worker)
python -m src.vector_db.kafka_conn.main

# Terminal 3: File Ops (port 8002)
python -m src.file_ops.endpoints.main

# Terminal 4: LLM Service (port 8001)
python -m src.llm.endpoints.main

# Terminal 5: Gateway (port 8000)
python -m src.gateway_auth.endpoints.main

# Terminal 6: UI
cd ui && npm install && npm run dev
```

---

## API Endpoints

### Gateway (port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/gateway/ai_agent` | AI-powered semantic search |
| GET | `/gateway/get_objects` | List files from cloud storage |
| POST | `/gateway/upload_object` | Upload file to cloud storage |
| DELETE | `/gateway/delete_object` | Delete file from cloud storage |
| PUT | `/gateway/rename_object` | Rename file in cloud storage |
| GET | `/gateway/download_object` | Download file from cloud storage |
| GET | `/events/user/{owner}` | Get user event history |
| WS | `/ws/events/{owner}` | Real-time event updates |
| GET | `/auth/google/url` | Get Google OAuth URL |
| POST | `/auth/google/callback` | Handle OAuth callback |

### File Ops (port 8002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/get_all` | List files from storage |
| POST | `/upload` | Upload file to storage |
| DELETE | `/delete` | Delete file from storage |
| PUT | `/rename` | Rename file in storage |
| GET | `/download` | Download file from storage |

### LLM Service (port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/get_response` | Get AI response with RAG context |

---

## Testing

The project uses a comprehensive 4-tier testing strategy:

```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit        # Unit tests (fast, mocked)
pytest -m integration # Integration tests (TestClient)
pytest -m system      # System tests (E2E flows)
pytest -m acceptance  # Acceptance tests (user scenarios)

# With coverage
pytest --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── unit/                    # 17 files, ~115 tests
│   ├── test_event_db_*.py
│   ├── test_file_ops_*.py
│   ├── test_gateway_auth_*.py
│   ├── test_vector_db_*.py
│   ├── test_llm_*.py
│   └── test_kafka_*.py
├── integration/             # 4 files, ~25 tests
│   ├── test_event_db_api.py
│   ├── test_file_ops_api.py
│   ├── test_gateway_auth_api.py
│   └── test_llm_api.py
├── system/                 # 1 file, 8 tests
│   └── test_e2e_flows.py
└── acceptance/             # 1 file, 11 tests
    └── test_user_scenarios.py
```

**Total: 191 tests, all passing**

---

## Key Concepts

### Semantic Search

The system uses embeddings to understand file content:

1. User enters natural language query (e.g., "quarterly financial report")
2. Query is converted to embedding vector using OpenAI's `text-embedding-3-small`
3. Vector DB performs similarity search against stored file embeddings
4. Top-K most relevant files are returned
5. LLM generates answer using retrieved file context (RAG)

### Event System

All file operations trigger events stored in Event DB:

| Event | Description |
|-------|-------------|
| `uploading` | File upload started |
| `uploaded` | File upload completed |
| `updating` | File update started |
| `deleting` | File deletion started |
| `renaming` | File rename started |

Events are displayed in real-time on the UI via WebSocket.

### Adapter Pattern

Each domain follows the adapter pattern for flexibility:

```
domain/          → Interfaces and business logic (pure Python)
adapters/        → Concrete implementations (PostgreSQL, GCS, Google Drive)
```

This allows swapping storage backends or LLM providers without changing core logic.

---

## Environment Variables Reference

### Required for All Services

```bash
# Kafka
BROKER_HOSTS=localhost:9092
```

### Vector DB Service

```bash
DOCS_POSTGRESQL_USERNAME=postgres
DOCS_POSTGRESQL_PASSWORD=your_password
DOCS_POSTGRESQL_HOST=localhost
DOCS_POSTGRESQL_PORT=5432
DOCS_POSTGRESQL_DB=vector_db
REQUEST_TOPICS=request_from_agent,request_from_gcs,request_from_gd
REPLY_EVENT_TOPIC=send_event
```

### Event DB Service

```bash
EVENT_POSTGRESQL_USERNAME=postgres
EVENT_POSTGRESQL_PASSWORD=your_password
EVENT_POSTGRESQL_HOST=localhost
EVENT_POSTGRESQL_PORT=5432
EVENT_POSTGRESQL_DB=events_db
REQUEST_TOPICS=send_event
```

### File Ops Service

```bash
GCS_BUCKET_NAME=your_bucket
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REQUEST_TOPICS=request_from_gcs,request_from_gd
REPLY_TOPIC=send_event
EVENT_DB_TOPIC=send_event
```

### LLM Service

```bash
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-...
MODEL=gpt-4
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Gateway Service

```bash
OAUTH_GOOGLE_CLIENT_ID=...
OAUTH_GOOGLE_CLIENT_SECRET=...
OAUTH_GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
AGENT_SERVER=http://localhost:8001
FILE_OPS_SERVER=http://localhost:8002
EVENT_DB_URL=http://localhost:8003
```

---

## Troubleshooting

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Create database with pgvector extension
docker exec -it semantic-postgres psql -U postgres -d postgres -c "CREATE DATABASE vector_db;"
docker exec -it semantic-postgres psql -U postgres -d vector_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Kafka Not Responding

```bash
# Check Kafka status
docker ps | grep kafka
docker logs llm-semantic-kafka

# Recreate topics if needed
docker exec -it llm-semantic-kafka kafka-topics --create --topic send_event --bootstrap-server localhost:9092
```

### Tests Failing

```bash
# Run tests with verbose output
pytest -v --tb=long

# Run specific test file
pytest tests/unit/test_event_db_domain.py -v
```

---

## License

MIT License

---

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting a pull request.

```bash
# Run full test suite before committing
pytest -v
```