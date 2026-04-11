"""
Run the server:
    uvicorn src.llm.endpoints.main:app --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.system.file_ops.endpoints.main import app as file_ops_app

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

for router in file_ops_app.routes:
    if hasattr(router, "tags"):
        app.router.routes.append(router)

agent_researcher = AgentResearcher()


@app.get("/ai_agent")
async def get_response_from_ai_agent(text: str) -> SearchResponse:
    query = SearchRequest(text=text, file_path=None)
    response = agent_researcher.get_response(query)
    return response
