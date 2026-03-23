from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.llm.agent_web_rag.domain.domain import SearchResponse, SearchRequest
from src.llm.agent_web_rag.adapters.agent import AgentResearcher

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_researcher = AgentResearcher()

@app.get("/research_agent")
async def get_response_from_web_research_and_rag_agent(text: str, file_path: str | None = None) -> SearchResponse:
    query = SearchRequest(text=text, file_path=file_path)
    response = agent_researcher.get_response(query)
    return response
