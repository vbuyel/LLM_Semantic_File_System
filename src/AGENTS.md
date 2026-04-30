# BACKEND SOURCE KNOWLEDGE BASE

## OVERVIEW
Multi-service backend architecture implementing semantic search, vector storage, and file operations.

## STRUCTURE
```
src/
├── llm/            # LLM integration and semantic analysis
├── vector_db/      # Vector database adapters (Qdrant, etc.)
├── file_ops/       # File system operations and cloud adapters
└── gateway_auth/   # Authentication gateway and OAuth handling
```

## ARCHITECTURE PATTERN
Each service follows a similar structure:
- `domain/`: Business logic and interfaces.
- `adapters/`: Concrete implementations (DBs, APIs, FS).
- `endpoints/`: API route definitions.

## CONVENTIONS
- Use Dependency Injection for adapters.
- Maintain strict separation between domain logic and infra adapters.
- Use `__pycache__` exclusions in git.

## ANTI-PATTERNS
- Avoid cross-service imports where possible; use the gateway.
- Do not store secrets in the codebase; use environment variables.
