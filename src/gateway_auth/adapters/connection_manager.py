from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.last_event_ids: dict[str, int] = {}


    async def connect(self, owner: str, websocket: WebSocket):
        await websocket.accept()
        if owner not in self.active_connections:
            self.active_connections[owner] = []
        self.active_connections[owner].append(websocket)


    def disconnect(self, owner: str, websocket: WebSocket):
        if owner in self.active_connections:
            self.active_connections[owner] = [
                ws for ws in self.active_connections[owner] if ws != websocket
            ]
            if not self.active_connections[owner]:
                del self.active_connections[owner]


    async def broadcast_to_owner(self, owner: str, message: dict):
        if owner in self.active_connections:
            dead_ws = []
            for ws in self.active_connections[owner]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_ws.append(ws)
            for ws in dead_ws:
                self.disconnect(owner, ws)
