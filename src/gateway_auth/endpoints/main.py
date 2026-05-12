"""
Run the server:
    uvicorn src.gateway_auth.endpoints.main:app --port 8000
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.gateway_auth.endpoints.gateway_router import gateway_router
from src.gateway_auth.endpoints.oauth_router import oauth_router
from src.gateway_auth.endpoints.events_router import router as events_router
from src.gateway_auth.endpoints.events_ws import manager, start_events_polling


app = FastAPI()
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


@app.on_event("startup")
async def startup_event():
    start_events_polling()


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
