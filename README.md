# LLM Semantic File System

<p align="center">
  <strong>AI-Driven File Management with Semantic Search</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#for-developers">For Developers</a> •
  <a href="#api-reference">API Reference</a>
</p>

---

## What is Semantic FS?

Semantic FS is an intelligent file management system that combines traditional file operations with AI-powered semantic search. Store your files in Google Drive or Google Cloud Storage, then use natural language to find exactly what you need — the system understands the *content* of your files, not just their names.

### For End Users

**Key Benefits:**

- **Semantic Search**: Ask questions like "Where is my resume?" or "Find the project proposal from last month" — the AI understands your files' content
- **AI Assistant**: Chat with an AI that has access to both the web and your personal files
- **Multiple Storage Options**: Choose between Google Drive or Google Cloud Storage
- **Modern Interface**: Clean, dark-themed UI with real-time event tracking

**How to Use:**

1. Open the web interface at `http://localhost:5500`
2. Sign in with your Google account (OAuth)
3. Upload files or connect your Google Drive
4. Use the AI chat to find files by asking natural language questions
5. Manage files: upload, download, rename, delete — all from the browser

**Example Queries:**

- "Find my tax documents from 2024"
- "Show me the Python script about data processing"
- "What files contain information about the project timeline?"

### For Software Engineers

**System Overview:**

Semantic FS is a microservices-based application with the following components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (UI)                          │
│                    http://localhost:5500                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gateway (Port 8000)                         │
│               Authentication & Request Routing                 │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   LLM Svc    │    │  File Ops    │    │  Vector DB   │
│   (8001)     │    │   (8002)     │    │   (8004)     │
│              │    │              │    │              │
│ AI Agent     │    │ Upload/Down  │    │ Semantic     │
│ Web Search   │    │ List/Delete  │    │ Search       │
│ RAG Search   │    │ Rename       │    │ Embeddings   │
└──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Kafka Broker (Events)                       │
└─────────────────────────────────────────────────────────────────┘
```

**Technology Stack:**

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI (Python) |
| Frontend | Vanilla JavaScript + Vite |
| Vector Database | PostgreSQL + pgvector |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| LLM Backend | Ollama (local) / OpenAI / Anthropic |
| Event Streaming | Kafka |
| Storage | Google Cloud Storage, Google Drive API |
| Authentication | Google OAuth 2.0, JWT |
| Search API | Exa (web search) |

**Microservices:**

| Service | Port | Purpose |
|---------|------|---------|
| Gateway | 8000 | Auth gateway, request routing |
| LLM | 8001 | AI agent, tool calling, RAG |
| File Ops | 8002 | File CRUD operations |
| Event DB | 8003 | Event persistence |
| Vector DB | 8004 | Semantic search, embeddings |

---

## Features

### AI-Powered Search

- **Semantic Understanding**: Uses vector embeddings to find files by content similarity
- **Natural Language Queries**: Ask questions in plain English
- **Hybrid Search**: Combines RAG (files) with web search when needed

### File Management

- **Upload**: Drag-and-drop or browse to upload files
- **Download**: Download any file from your storage
- **Rename**: Rename files with ease
- **Delete**: Remove files with confirmation
- **Multi-Storage**: Seamlessly switch between GCS and Google Drive

### AI Assistant

- **Tool-Calling Agent**: Intelligent agent that decides when to search files vs. the web
- **Web Search**: Real-time web search for general queries
- **File Context**: Full access to your indexed files for personalized answers

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Google Cloud Console project (for OAuth)

### Setup Steps

**1. Clone and Configure:**

```bash
# Clone the repository
git clone <repository-url>
cd LLM_Semantic_File_System

# Copy environment template
cp .env.example .env
```

**2. Configure Environment Variables:**

Edit `.env` with your credentials:

```env
# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# JWT Secret (generate a random string)
JWT_SECRET=your_jwt_secret

# LLM Configuration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Exa Search (optional)
EXA_API_KEY=your_exa_key

# Google Cloud Storage
GCS_BUCKET_NAME=your_bucket

# PostgreSQL for Vector DB
DOCS_POSTGRESQL_USERNAME=postgres
DOCS_POSTGRESQL_PASSWORD=postgres
DOCS_POSTGRESQL_HOST=localhost
DOCS_POSTGRESQL_PORT=5432
DOCS_POSTGRESQL_DB=documents

# Ollama (local LLM)
MODEL=llama3
```

**3. Start Services:**

```bash
# Start infrastructure (Kafka, PostgreSQL)
cd src/kafka && docker-compose up -d
python -m src.kafka.broker &

# Start all microservices
uvicorn src.gateway_auth.v1.main:app --port 8000 &
uvicorn src.llm.v1.main:app --port 8001 &
uvicorn src.file_ops.v1.main:app --port 8002 &
uvicorn src.event_db.v1.main:app --port 8003 &
uvicorn src.vector_db.v1.main:app --port 8004 &

# Start frontend
cd ui && npx serve -s . -p 5500
```

**Or use the convenience script:**

```bash
# Each line from .run_services
```

**4. Access the Application:**

Open `http://localhost:5500` in your browser and sign in with Google.

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud Console | Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | Yes |
| `JWT_SECRET` | Secret for JWT token signing | Yes |
| `OPENAI_API_KEY` | OpenAI API key | No* |
| `ANTHROPIC_API_KEY` | Anthropic API key | No* |
| `EXA_API_KEY` | Exa web search API key | No |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket | Yes |
| `DOCS_POSTGRESQL_*` | PostgreSQL connection for vector DB | Yes |

*At least one LLM provider is required.

### Service Configuration

Each microservice has its own `.env` in its directory. The main configuration is in the project root `.env`.

---

## For Developers

### Project Structure

```
LLM_Semantic_File_System/
├── src/
│   ├── gateway_auth/      # Authentication gateway
│   ├── llm/              # AI agent, RAG, web search
│   ├── file_ops/         # File operations (GCS, Drive)
│   ├── event_db/         # Event persistence
│   ├── vector_db/        # Semantic search (pgvector)
│   └── kafka/            # Event streaming
├── ui/                   # Frontend (HTML/CSS/JS)
├── tests/                # Test suite
└── .run_services         # Startup commands
```

### Key Modules

**LLM Service (`src/llm/`):**
- `adapters/agent.py` — AI agent with tool-calling (RAG + web search)
- `adapters/rag_search.py` — Semantic file search
- `adapters/web_search.py` — Exa-powered web search

**File Operations (`src/file_ops/`):**
- `adapters/gcs_ops.py` — Google Cloud Storage operations
- `adapters/google_drive_ops.py` — Google Drive API integration
- `adapters/text_extractor.py` — Extract text from files for indexing

**Vector Database (`src/vector_db/`):**
- `adapters/database.py` — PostgreSQL + pgvector for semantic search
- Uses sentence-transformers for embeddings

### Adding New Features

**To add a new storage provider:**

1. Create an adapter in `src/file_ops/adapters/`
2. Implement the same interface as `GCSOperations` or `GoogleDriveOperations`
3. Update the API in `src/file_ops/v1/main.py` to handle the new provider

**To add a new LLM provider:**

1. Modify `src/llm/adapters/agent.py`
2. The agent currently uses OpenAI-compatible API (Ollama)
3. Add new tool definitions for additional capabilities

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file_ops.py -v
```

---

## API Reference

### Gateway (Port 8000)

- `GET /health` — Health check

### LLM Service (Port 8001)

- `GET /health` — Health check
- `POST /get_response` — Get AI response with tool access

**Request:**
```json
{
  "text": "Find my resume",
  "owner": "user@example.com",
  "correlation_id": "uuid"
}
```

**Response:**
```json
{
  "text": "Found your resume at /documents/resume_2024.pdf"
}
```

### File Operations (Port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload a file |
| `/get_all` | GET | List files in directory |
| `/delete` | DELETE | Delete a file |
| `/rename` | PUT | Rename a file |
| `/download` | GET | Download a file |

All endpoints require headers:
- `X-Owner`: User email
- `X-Auth-Provider`: "google" or "local"
- `X-Storage-Source`: "gcs" or "drive"

### Vector Database (Port 8004)

Used internally for semantic search. Exposes endpoints for:
- Document indexing
- Semantic search
- Document deletion/renaming

---

## Troubleshooting

### Common Issues

**LLM not responding:**
- Ensure Ollama is running: `ollama serve`
- Check the model is available: `ollama list`

**Files not searchable:**
- Check PostgreSQL connection
- Verify vector extension is installed: `CREATE EXTENSION vector`

**OAuth not working:**
- Verify redirect URIs in Google Cloud Console
- Check client ID and secret in `.env`

### Logs

Check individual service logs in their respective Docker containers or terminal output.

---

## License

MIT License

---

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.