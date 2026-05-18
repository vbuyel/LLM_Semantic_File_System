# LLM Semantic File System (Semantic FS)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Apache%20Kafka-Event--Driven-808080.svg?style=for-the-badge&logo=apache-kafka&logoColor=white" alt="Kafka" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

<p align="center">
  <strong>An Intelligent, Event-Driven Microservices Platform with AI-Powered Semantic Search & Multi-Storage Support</strong>
</p>

---

## Table of Contents

- [What is Semantic FS?](#-what-is-semantic-fs)
  - [For End Users](#-for-end-users)
  - [For Developers](#-for-developers)
- [System Architecture](#️-system-architecture)
  - [Microservice Architecture Diagram](#microservice-architecture-diagram)
  - [Event-Driven Data Flow](#event-driven-data-flow)
- [Tech Stack & Microservices](#️-tech-stack--microservices)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [1. Clone & Configure](#1-clone--configure)
  - [2. Spin up Services (Convenient Way)](#2-spin-up-services-convenient-way)
  - [3. Spin up Services (Manual Way)](#3-spin-up-services-manual-way)
- [Testing Strategy](#-testing-strategy)
  - [The Global pytest Import Conflict](#the-global-pytest-import-conflict)
  - [The Solution: Service-Specific Environments](#the-solution-service-specific-environments)
  - [Running All Tests Sequentially](#running-all-tests-sequentially)
- [API Reference](#-api-reference)
  - [Gateway Service (Port 8000)](#gateway-service-port-8000)
  - [LLM Service (Port 8001)](#llm-service-port-8001)
  - [File Operations Service (Port 8002)](#file-operations-service-port-8002)
  - [Vector Database Service (Port 8004)](#vector-database-service-port-8004)
- [Troubleshooting](#-troubleshooting)

---

## What is Semantic FS?

**Semantic FS** is a modern, high-performance file management system that elevates traditional file operations with AI-powered semantic search. Instead of relying solely on exact filename matches, the system indexes the *actual textual content* of your files and understands user intent using Natural Language Processing (NLP).

### For End Users

- **Semantic Content Search**: Find your files by asking natural language questions like *"Where is my resume?"*, *"Find the tax invoice from last year"*, or *"Show me the Python script that processes data"*.
- **Autonomous AI Assistant**: Chat with a persistent AI assistant that can seamlessly switch between searching your files (RAG) and searching the web to answer your questions.
- **Unified Storage Interface**: Seamlessly switch between **Google Cloud Storage (GCS)** and **Google Drive** directly from a single web dashboard.
- **Premium Real-Time Dashboard**: Monitor file uploads, database syncs, and event logs in a beautiful, responsive dark-themed user interface.

### For Developers

- **Strict Separation of Concerns**: Built as 5 completely autonomous, decoupled FastAPI microservices, each with its own package configuration (`requirements.txt`) and dedicated virtual environment (`.venv`).
- **Event-Driven & Asynchronous**: Utilizes **Apache Kafka** for streaming events, such as tracking file uploads, background document extraction, and vector index synchronization.
- **Robust Local Testing**: Comprehensive test coverage across all layers of the codebase (unit and system tests) running in fully isolated testing environments.

---

## System Architecture

### Microservice Architecture Diagram

```mermaid
graph TD
    UI[Frontend Dashboard<br/>Port 5500] <-->|HTTP / WebSockets| GW[Gateway & Auth Service<br/>Port 8000]
    
    GW <-->|REST API| LLM[LLM Service<br/>Port 8001]
    GW <-->|REST API| FO[File Operations Service<br/>Port 8002]
    
    FO -.->|Upload / Sync Events| Kafka[(Apache Kafka<br/>Port 9092)]
    
    Kafka -->|Consumer: Index Documents| VDB[Vector Database Service<br/>Port 8004]
    Kafka -->|Consumer: Persist Logs| EDB[Event DB Service<br/>Port 8003]
    
    EDB <-->|WebSockets / HTTP| GW
    
    VDB <-->|PostgreSQL + pgvector| PG[(PostgreSQL Database<br/>Port 5432)]
    FO <-->|Storage Drivers| GCS[Google Cloud Storage]
    FO <-->|Storage Drivers| GD[Google Drive API]
```

### Event-Driven Data Flow

1. **File Upload**: The user uploads a file via the UI.
2. **Text Extraction**: The **File Operations Service** (`file_ops`) saves the file, parses its format (PDF, DOCX, TXT, etc.), extracts textual chunks, and publishes an `upload` event to Kafka.
3. **Semantic Indexing**: The **Vector Database Service** (`vector_db`) consumes the event, converts text chunks into 384-dimensional dense vectors using a Sentence Transformer model, and indexes them in **PostgreSQL + pgvector**.
4. **Activity Logging**: The **Event DB Service** (`event_db`) consumes the Kafka event, records it in the PostgreSQL event log, and forwards the log in real-time to the Gateway WebSocket for UI notifications.

---

## Tech Stack & Microservices

| Service Name | Default Port | Primary Responsibilities | Stack / Dependencies |
| :--- | :---: | :--- | :--- |
| **Gateway** | `8000` | User Authentication (Google OAuth 2.0, JWT), API reverse proxying, event relay via WebSockets. | FastAPI, Python-JWT, HTTPX |
| **LLM Service** | `8001` | Tool-calling AI agent, prompt orchestration, Exa-powered web search, and local/remote LLM interface. | FastAPI, OpenAI SDK, Exa API |
| **File Operations** | `8002` | Upload, download, delete, rename, text extraction, and OAuth client integration. | FastAPI, google-cloud-storage, google-api-python-client |
| **Event DB** | `8003` | Persistent storage of system action logs, history search, and real-time WebSocket push. | FastAPI, psycopg (PostgreSQL), AIOKafka |
| **Vector DB** | `8004` | Generating text embeddings, querying cosine distance, indexing text chunks, and pgvector operations. | FastAPI, sentence-transformers, pgvector, psycopg |
| **Kafka Infrastructure** | `9092` | Decoupled event broker. | Apache Kafka (Docker) |

---

## Quick Start

### Prerequisites

Make sure you have the following installed on your system:
- **Docker** and **Docker Compose**
- **Python 3.11 or 3.13+**
- **Node.js** (for simple static server serving the UI)

---

### 1. Clone & Configure

1. Clone this repository to your local system:
   ```bash
   git clone <repository-url>
   cd LLM_Semantic_File_System
   ```
2. Create and fill in your root-level environment configuration file:
   ```bash
   cp .env.example .env
   ```
3. Edit the `.env` file with your credentials:
   ```env
   # Google OAuth Credentials (obtain from Google Cloud Console)
   GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   
   # JWT Configuration
   JWT_SECRET=your_jwt_signature_secret_key
   
   # LLM Backend Configuration
   OPENAI_API_KEY=sk-proj-... # Optional if using Ollama
   MODEL=gpt-4o-mini          # or local ollama models like llama3
   
   # Web Search API (Optional)
   EXA_API_KEY=your_exa_search_api_key
   
   # Cloud Storage Buckets
   GCS_BUCKET_NAME=your-gcs-bucket-name
   
   # PostgreSQL Connection Info (Vector DB & Event DB)
   DOCS_POSTGRESQL_USERNAME=postgres
   DOCS_POSTGRESQL_PASSWORD=postgres
   DOCS_POSTGRESQL_HOST=localhost
   DOCS_POSTGRESQL_PORT=5432
   DOCS_POSTGRESQL_DB=documents
   ```

---

### 2. Spin up Services (Convenient Way)

We have provided a premium, fully automated orchestration script: [run_services.sh](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/run_services.sh). It will automatically start Kafka, create topics, run all 5 microservices in their correct virtual environments, start the Frontend UI, and log everything nicely.

```bash
# Run the orchestration script
./run_services.sh
```

To stop all background microservices, simply press `Ctrl+C` in your terminal. The script will trap the signal and shut everything down safely!

---

### 3. Spin up Services (Manual Way)

If you prefer starting services manually in separate terminals, follow this order:

1. **Start Kafka Docker container**:
   ```bash
   cd src/kafka && docker-compose up -d
   ```
2. **Initialize Kafka topics**:
   ```bash
   # From project root using any service environment
   ./src/file_ops/.venv/bin/python src/kafka/broker.py
   ```
3. **Run individual microservices**:
   - **Gateway (Port 8000)**:
     ```bash
     cd src/gateway_auth && ./.venv/bin/uvicorn v1.main:app --port 8000
     ```
   - **LLM Service (Port 8001)**:
     ```bash
     cd src/llm && ./.venv/bin/uvicorn v1.main:app --port 8001
     ```
   - **File Operations (Port 8002)**:
     ```bash
     cd src/file_ops && ./.venv/bin/uvicorn v1.main:app --port 8002
     ```
   - **Event DB (Port 8003)**:
     ```bash
     cd src/event_db && ./.venv/bin/uvicorn v1.main:app --port 8003
     ```
   - **Vector DB (Port 8004)**:
     ```bash
     cd src/vector_db && ./.venv/bin/uvicorn v1.main:app --port 8004
     ```
4. **Run the static UI Frontend (Port 5500)**:
   ```bash
   cd ui && npx serve -s . -p 5500
   ```

---

## Testing Strategy

### The Global `pytest` Import Conflict

Since each microservice is a completely decoupled Python project containing duplicate top-level package names (such as `domain` and `adapters`), running a simple global command like:
```bash
pytest -v
```
from the root directory **will fail with 24+ ModuleNotFoundError/ImportError conflicts**. This is because Python's module discovery mechanism gets confused about which service's `domain.domain` or `adapters` package to import.

### The Solution: Service-Specific Environments

To resolve this completely, all tests should be executed *within* their individual service directories using their local virtual environments (`.venv/bin/pytest`), ensuring 100% test isolation.

### Running All Tests Sequentially

We have created an automated test runner script [run_tests.sh](file:///Users/vladbuyel/Documents/Projects/LLM_Semantic_File_System/run_tests.sh) in the workspace root. It traverses through each microservice, activates its specific virtual environment, and executes its complete suite of system and unit tests:

```bash
# Run all tests cleanly
./run_tests.sh
```

If you want to run tests for a specific service manually:
```bash
cd src/file_ops
./.venv/bin/pytest -v
```

---

## API Reference

### Gateway Service (Port 8000)
- `GET /health` — Simple health check.
- `POST /get_response` — Route user queries directly to the LLM service.
- `GET /events/user/{owner}` — Fetch past user logs and system actions.

### LLM Service (Port 8001)
- `GET /health` — Check LLM service health.
- `POST /get_response` — Query tool-calling AI agent.
  - **Payload Structure**:
    ```json
    {
      "text": "What is inside my taxes file?",
      "owner": "user@example.com",
      "correlation_id": "optional-uuid"
    }
    ```

### File Operations Service (Port 8002)
- `GET /health` — Health check.
- `POST /upload` — Upload physical files to Google Cloud Storage or Google Drive.
- `GET /get_all` — Retrieve list of files.
- `DELETE /delete` — Delete file from active storage.
- `PUT /rename` — Rename file in storage.
- `GET /download` — Fetch download link/bytes of file.

> [!NOTE]
> All File Operations API routes require the following headers:
> - `X-Owner`: User Email Address (e.g. `user@example.com`)
> - `X-Auth-Provider`: `google` or `local`
> - `X-Storage-Source`: `gcs` or `drive`

### Vector Database Service (Port 8004)
- `GET /check-file-exists` — Checks whether a file with matching path/size has already been embedded to prevent redundant indexing.

---

## Troubleshooting

### Python Module Mismatch / `ModuleNotFoundError` during `pytest`
- **Cause**: Running `pytest` from the root workspace folder.
- **Solution**: Execute tests via `./run_tests.sh` or navigate to the specific service directory (e.g., `src/file_ops`) and run tests using local virtualenv binaries: `./.venv/bin/pytest -v`.

### `TopicAlreadyExistsError` or Kafka Connection Refused
- **Cause**: Kafka is either not running or the topics are currently being created in the background.
- **Solution**: Run `docker ps` to verify the `llm-semantic-kafka` container is active. If needed, restart it:
  ```bash
  cd src/kafka && docker-compose down && docker-compose up -d
  ```

### `CREATE EXTENSION vector` failure on PostgreSQL startup
- **Cause**: Your local PostgreSQL database does not have the `pgvector` extension installed.
- **Solution**: Run your PostgreSQL database via Docker with `pgvector` built-in, or install it on your OS (e.g., via Homebrew on macOS: `brew install pgvector`).
