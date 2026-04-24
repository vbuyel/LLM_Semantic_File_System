"""
Run the server:
    uvicorn src.llm.endpoints.main:app --port 8003
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


@app.get("/ai_agent")
async def get_response_from_ai_agent(text: str) -> SearchResponse:
    query = SearchRequest(text=text)
    response = agent_researcher.get_response(query)
    print(f"[DEBUG] Full response: {response}")
    print(f"[DEBUG] response.text: {response.text}")
    return response
