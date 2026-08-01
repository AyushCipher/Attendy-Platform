import asyncio
import json

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.services.attendance_service import mark_present_if_new
from app.services.face_engine import get_face_engine
from app.services.matcher import find_best_match, get_student_if_active
from app.services.tracker import FaceTracker
from app.ws.connection_manager import attendance_feed_manager

router = APIRouter()


@router.websocket("/ws/recognize")
async def recognize(websocket: WebSocket, token: str, db: AsyncSession = Depends(get_db)):
    try:
        decode_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    engine = get_face_engine()
    tracker = FaceTracker()

    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            image = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                continue

            faces = await asyncio.to_thread(engine.detect, image)
            results = []

            for face in faces:
                match = await find_best_match(db, face.embedding)
                matched_student_id = match.student_id if (match and match.is_match) else None
                similarity = match.similarity if match else 0.0

                smoothed = tracker.update(face.bbox, matched_student_id, similarity)

                entry = {
                    "bbox": face.bbox,
                    "status": "unknown",
                    "name": None,
                    "similarity": round(smoothed.similarity, 4),
                    "live": smoothed.live,
                }

                if smoothed.confirmed and smoothed.student_id:
                    student = await get_student_if_active(db, smoothed.student_id)
                    if student is None:
                        entry["status"] = "unknown"
                    elif tracker.already_recorded(face.bbox):
                        entry["status"] = "already_marked"
                        entry["name"] = student.name
                    else:
                        record = await mark_present_if_new(
                            db,
                            student_id=student.id,
                            class_section_id=student.class_section_id,
                            confidence=smoothed.similarity,
                        )
                        entry["name"] = student.name
                        if record is not None:
                            entry["status"] = "confirmed"
                            tracker.mark_recorded(student.id)
                            await attendance_feed_manager.broadcast(
                                {
                                    "type": "attendance_confirmed",
                                    "student_id": str(student.id),
                                    "name": student.name,
                                    "roll_number": student.roll_number,
                                    "class_section": {
                                        "id": str(student.class_section.id),
                                        "grade": student.class_section.grade,
                                        "section": student.class_section.section,
                                        "label": student.class_section.label,
                                    },
                                    "event_time": record.event_time.isoformat(),
                                    "confidence": smoothed.similarity,
                                    "source": "face",
                                }
                            )
                        else:
                            entry["status"] = "already_marked"
                            tracker.mark_recorded(student.id)
                elif matched_student_id:
                    entry["status"] = "recognizing"

                results.append(entry)

            await websocket.send_text(json.dumps({"faces": results}))
    except WebSocketDisconnect:
        pass
    finally:
        pass  # nothing to clean up: tracker/engine are per-connection or process-wide
