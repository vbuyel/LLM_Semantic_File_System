"""
Run the server:
    uvicorn src.gateway_auth.endpoints.main:app --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.gateway_auth.endpoints.gateway_router import gateway_router
from src.gateway_auth.endpoints.oauth_router import oauth_router
from src.gateway_auth.endpoints.events_router import router as events_router
from src.gateway_auth.adapters.events_ws import manager, start_events_polling, stop_events_polling


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_events_polling()
    yield
    stop_events_polling()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length"],
)

app.include_router(gateway_router)
app.include_router(oauth_router)
app.include_router(events_router)


@app.websocket("/ws/events/{owner}")
async def websocket_events(websocket, owner: str):
    await manager.connect(owner, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(owner, websocket)


@app.get("/health")
def health_check():
    return {"status": "ok"}
