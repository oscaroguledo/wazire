"""
WebSocket connection manager + notification helper.

Clients connect to /ws/{user_id} and receive JSON push messages
whenever a background job changes status.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(user_id, None)

    async def send(self, user_id: str, payload: Dict[str, Any]) -> None:
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                self.disconnect(user_id, ws)

    async def broadcast_to_exam(self, exam_id: str, payload: Dict[str, Any]) -> None:
        """Broadcast to all users watching a specific exam."""
        # Send to all connected users for now (simplified)
        for user_id, conns in list(self._connections.items()):
            for ws in list(conns):
                try:
                    await ws.send_text(json.dumps({
                        **payload,
                        "exam_id": exam_id
                    }))
                except Exception:
                    self.disconnect(user_id, ws)


manager = ConnectionManager()


async def notify(user_id: str, payload: dict) -> None:
    """Send notification to a specific user."""
    await manager.send(user_id, payload)


async def notify_exam_update(exam_id: str, event_type: str, data: Optional[dict] = None) -> None:
    """Broadcast exam update to all connected clients."""
    await manager.broadcast_to_exam(exam_id, {
        "type": event_type,
        "exam_id": exam_id,
        "data": data or {},
        "timestamp": json.dumps(None)  # Client can add timestamp
    })
