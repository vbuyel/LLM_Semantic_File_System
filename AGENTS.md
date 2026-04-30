# PROJECT KNOWLEDGE BASE: LLM Semantic File System

**Generated:** 2026-04-30
**Commit:** local
**Branch:** main

## OVERVIEW
An AI-driven semantic file system that integrates local files with Google Drive and Cloud Storage. It uses LLMs for semantic search and file interaction.

## STRUCTURE
```
.
├── src/            # Core backend services (LLM, Vector DB, File Ops)
├── ui/             # Frontend (Vite, JS components, CSS)
├── tests/          # Integration and unit tests
└── .venv/          # Python virtual environment
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Backend Logic | `src/` | LLM, VectorDB, and Auth services |
| UI/Frontend | `ui/` | JS components and styles |
| Data Adapters | `src/*/adapters/` | Interface implementations |
| API Endpoints | `src/*/endpoints/` | Service entry points |

## CONVENTIONS
- **Backend**: Python-based services with distinct domain/adapter separation.
- **Frontend**: Vanilla JS with a component-based architecture and custom state management.
- **Icons**: Lucide icons used throughout the UI.

## ANTI-PATTERNS (THIS PROJECT)
- Avoid inline styles in components.
- Do not mix storage logic directly into UI components; use `api.js` and `state.js`.

## COMMANDS
```bash
# UI Development
cd ui && npm run dev

# Backend Services (refer to specific src subdirectories)
python src/gateway_auth/main.py
```

## NOTES
- The project is in a transitional state with specific UI changes pending (removing Local files, updating Guest login flow).
