import os
from sentence_transformers import SentenceTransformer

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from system.vector_db.adapters.repo_database import RepositoryDataBase
from src.system.vector_db.domain.domain import SearchResult

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Database
db = RepositoryDataBase()

# === Into Adapters ===
embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))

_bootstrap_servers = os.getenv("BROKER_HOSTS", "localhost:9092").split(",")
_request_topic = os.getenv("REQUEST_TOPIC", "service.requests")
_reply_topic = os.getenv("REPLY_TOPIC", "service.replies")
# ===


@app.post("/search")
async def search_text_endpoint(text: str, limit: int = 3):
    """
    Raw text -> encode to vector -> search -> return results
    """
    try:
        embedding = embedding_model.encode(text).tolist()
        results = db.search_similar(embedding, limit=limit)
        formatted_results = [SearchResult(**result) for result in results]
        return formatted_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
