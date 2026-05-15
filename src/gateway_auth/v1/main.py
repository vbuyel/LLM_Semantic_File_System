"""
Run the server:
    uvicorn src.gateway_auth.endpoints.main:app --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.gateway_auth.endpoints.gateway_router import gateway_router
from src.gateway_auth.endpoints.oauth_router import oauth_router
from src.gateway_auth.endpoints.events_router import event_router
from src.gateway_auth.adapters.events_ws import start_eventdb_relay, stop_eventdb_relay


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_eventdb_relay()
    yield
    stop_eventdb_relay()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length"],
)

app.include_router(gateway_router, prefix="/gateway")
app.include_router(oauth_router, prefix="/auth")
app.include_router(event_router, prefix="/events")


@app.get("/health")
def health_check():
    return {"status": "ok"}
