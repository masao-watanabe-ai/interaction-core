from typing import List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_local(self, event: dict) -> None:
        dead: List[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.remove(ws)

    async def broadcast(self, event: dict) -> None:
        from app.services.redis_client import publish_event
        published = await publish_event(event)
        if not published:
            await self.broadcast_local(event)


# モジュールレベルのシングルトン（単一プロセス内で共有）
manager = ConnectionManager()
