import json

from fastapi import WebSocket


class ConnectionManager:
    """In-memory pub/sub for the attendance-feed WS channel.

    Single-process is the right scale here (one admin, one demo deployment); a
    multi-instance deployment would swap this for Redis pub/sub without changing
    any caller code.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


attendance_feed_manager = ConnectionManager()
