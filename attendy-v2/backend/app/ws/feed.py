from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.ws.connection_manager import attendance_feed_manager

router = APIRouter()


@router.websocket("/ws/attendance-feed")
async def attendance_feed(websocket: WebSocket, token: str):
    try:
        decode_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await attendance_feed_manager.connect(websocket)
    try:
        while True:
            # Read-only channel; just keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        attendance_feed_manager.disconnect(websocket)
