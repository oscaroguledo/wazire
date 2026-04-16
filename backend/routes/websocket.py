from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websockets import manager

router = APIRouter()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive, handle ping/pong if needed
            data = await websocket.receive_text()
            # Echo back for health check
            await websocket.send_text(f'{"type": "pong", "received": {data}}')
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception:
        manager.disconnect(user_id, websocket)
