from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.llm.ai_gateway.adapters.agentic_ai import AgenticAI
from src.llm.ai_gateway.domain.domain import Request, Response


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

agentic_ai = AgenticAI()


@app.post("/get_response")
async def get_response(request: Request) -> Response:
    response = agentic_ai.get_response(request)
    return response
