from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.auth_service import decode_access_token
from app.services.websocket_service import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
) -> None:
    # 優先順位: query param token → Cookie access_token
    raw_token = token or websocket.cookies.get("access_token")
    user_id = decode_access_token(raw_token) if raw_token else None

    if user_id is None:
        await websocket.accept()
        await websocket.close(code=4001)
        return

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
