"""
Run the server:
    uvicorn src.llm.endpoints.main:app --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langfuse import get_client

from domain.domain import SearchResponse, SearchRequest
from adapters.agent import AgentResearcher


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # Ensure queued traces are sent on shutdown (long-running FastAPI still benefits)
    get_client().flush()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_researcher = AgentResearcher()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/get_response")
async def get_response_from_ai_agent(request: SearchRequest) -> SearchResponse:
    response = await agent_researcher.get_response(request)
    return response
