"""
Run the server:
    uvicorn src.llm.endpoints.main:app --port 8001
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.llm.domain.domain import SearchResponse, SearchRequest
from src.llm.adapters.agent import AgentResearcher


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_researcher = AgentResearcher()


@app.post("/get_response")
async def get_response_from_ai_agent(request: SearchRequest) -> SearchResponse:
    response = agent_researcher.get_response(request)
    return response
