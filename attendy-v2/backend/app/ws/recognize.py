import asyncio
import datetime
import json
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.db.models.book import Book
from app.db.models.student import Student
from app.services.attendance_service import mark_present_if_new
from app.services.face_engine import get_face_engine
from app.services.library_service import compute_fine, get_open_borrow, try_borrow
from app.services.matcher import find_best_match, get_student_if_active
from app.services.meal_service import mark_meal_if_new
from app.services.tracker import FaceTracker
from app.ws.connection_manager import attendance_feed_manager

router = APIRouter()

VALID_MODES = {"attendance", "mess", "library"}


def _decode_qr(image: np.ndarray, qr_detector: cv2.QRCodeDetector) -> tuple[str, list | None]:
    try:
        data, points, _ = qr_detector.detectAndDecode(image)
    except cv2.error:
        return "", None
    qr_points = points[0].tolist() if points is not None else None
    return data, qr_points


async def _mark_and_broadcast(
    db: AsyncSession, student: Student, confidence: float | None, source: str, mode: str
) -> bool:
    """Marks attendance/meal (idempotent per day) and broadcasts to
    /ws/attendance-feed only on the call that actually inserted the row. Shared by
    both the face and QR paths (and both attendance/mess modes) so there's exactly
    one place a given kind of record gets written and announced, regardless of which
    signal confirmed it.
    """
    if mode == "mess":
        record = await mark_meal_if_new(
            db, student_id=student.id, class_section_id=student.class_section_id, source=source
        )
        event_type = "meal_confirmed"
    else:
        record = await mark_present_if_new(
            db,
            student_id=student.id,
            class_section_id=student.class_section_id,
            confidence=confidence,
            source=source,
        )
        event_type = "attendance_confirmed"

    if record is None:
        return False

    await attendance_feed_manager.broadcast(
        {
            "type": event_type,
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
            "confidence": confidence,
            "source": source,
        }
    )
    return True


async def _handle_qr(
    db: AsyncSession, image: np.ndarray, qr_detector: cv2.QRCodeDetector, mode: str
) -> dict | None:
    data, qr_points = _decode_qr(image, qr_detector)
    if not data:
        return None

    try:
        student_id = uuid.UUID(data)
    except ValueError:
        return {"points": qr_points, "status": "unknown", "name": None}

    student = await get_student_if_active(db, student_id)
    if student is None:
        return {"points": qr_points, "status": "unknown", "name": None}

    # A decoded UUID is an exact, deterministic match -- unlike face similarity, there
    # is nothing probabilistic to smooth over across frames, so this marks on the
    # very first successful decode.
    marked = await _mark_and_broadcast(db, student, confidence=None, source="qr", mode=mode)
    return {
        "points": qr_points,
        "status": "confirmed" if marked else "already_marked",
        "name": student.name,
    }


def _student_brief(student: Student) -> dict:
    return {"id": str(student.id), "name": student.name}


async def _handle_library_frame(
    db: AsyncSession,
    image: np.ndarray,
    engine,
    tracker: FaceTracker,
    qr_detector: cv2.QRCodeDetector,
    state: dict,
) -> dict:
    """Two-step flow, held in `state` (a plain dict local to this WS connection --
    not the DB): step 1 identifies a student by face or QR (no book action yet);
    step 2, once identified, expects a book QR and completes a borrow or return.
    No temporal smoothing gate on the book scan (unlike face identification) -- a
    decoded book UUID is exact, nothing probabilistic to smooth over.
    """
    current_student: Student | None = state.get("current_student")

    if current_student is None:
        faces = await asyncio.to_thread(engine.detect, image)
        tracks = tracker.assign([face.bbox for face in faces])
        face_results = []
        identified: Student | None = None

        for face, track in zip(faces, tracks, strict=True):
            match = await find_best_match(db, face.embedding)
            matched_student_id = match.student_id if (match and match.is_match) else None
            similarity = match.similarity if match else 0.0
            smoothed = tracker.update_track(track, matched_student_id, similarity)

            entry_status, name = "unknown", None
            if smoothed.confirmed and smoothed.student_id:
                student = await get_student_if_active(db, smoothed.student_id)
                if student is not None:
                    identified = student
                    entry_status, name = "confirmed", student.name
            elif matched_student_id:
                entry_status = "recognizing"

            face_results.append(
                {
                    "bbox": face.bbox,
                    "status": entry_status,
                    "name": name,
                    "similarity": round(smoothed.similarity, 4),
                    "live": smoothed.live,
                }
            )

        qr_result = None
        if identified is None:
            data, qr_points = _decode_qr(image, qr_detector)
            if data:
                try:
                    student = await get_student_if_active(db, uuid.UUID(data))
                except ValueError:
                    student = None
                if student is not None:
                    identified = student
                    qr_result = {"points": qr_points, "status": "confirmed", "name": student.name}
                else:
                    qr_result = {"points": qr_points, "status": "unknown", "name": None}

        if identified is not None:
            state["current_student"] = identified
            return {
                "stage": "awaiting_book",
                "student": _student_brief(identified),
                "book": None,
                "action": None,
                "message": f"Now scan the book for {identified.name}",
                "faces": face_results,
                "qr": qr_result,
            }

        return {
            "stage": "identifying",
            "student": None,
            "book": None,
            "action": None,
            "message": None,
            "faces": face_results,
            "qr": qr_result,
        }

    # Step 2: a student is identified, waiting on a book QR.
    data, qr_points = _decode_qr(image, qr_detector)
    if not data:
        return {
            "stage": "awaiting_book",
            "student": _student_brief(current_student),
            "book": None,
            "action": None,
            "message": None,
            "faces": [],
            "qr": None,
        }

    try:
        book_id = uuid.UUID(data)
    except ValueError:
        return {
            "stage": "awaiting_book",
            "student": _student_brief(current_student),
            "book": None,
            "action": "rejected",
            "message": "Not a recognized book QR",
            "faces": [],
            "qr": {"points": qr_points, "status": "unknown", "name": None},
        }

    book = await db.get(Book, book_id)
    if book is None or book.status != "active":
        return {
            "stage": "awaiting_book",
            "student": _student_brief(current_student),
            "book": None,
            "action": "rejected",
            "message": "Unknown book",
            "faces": [],
            "qr": {"points": qr_points, "status": "unknown", "name": None},
        }

    open_borrow = await get_open_borrow(db, book.id)
    student_brief = _student_brief(current_student)

    if open_borrow is None:
        state["current_student"] = None
        borrow = await try_borrow(db, book.id, current_student.id, current_student.class_section_id)
        if borrow is None:
            # Lost the race: another scan of this same book committed first between
            # our get_open_borrow() check above and this insert.
            return {
                "stage": "done",
                "student": student_brief,
                "book": {"id": str(book.id), "name": book.name},
                "action": "rejected",
                "message": f"{book.name} was just borrowed by someone else",
                "faces": [],
                "qr": {"points": qr_points, "status": "unknown", "name": book.name},
            }
        return {
            "stage": "done",
            "student": student_brief,
            "book": {"id": str(book.id), "name": book.name},
            "action": "borrowed",
            "message": f"{book.name} borrowed by {current_student.name}",
            "faces": [],
            "qr": {"points": qr_points, "status": "confirmed", "name": book.name},
        }

    if open_borrow.student_id == current_student.id:
        now = datetime.datetime.now(datetime.timezone.utc)
        open_borrow.returned_at = now
        open_borrow.fine_amount = compute_fine(open_borrow.borrowed_at, now)
        await db.commit()
        state["current_student"] = None
        fine_note = f" — fine ₹{open_borrow.fine_amount}" if open_borrow.fine_amount else ""
        return {
            "stage": "done",
            "student": student_brief,
            "book": {"id": str(book.id), "name": book.name},
            "action": "returned",
            "message": f"{book.name} returned by {current_student.name}{fine_note}",
            "faces": [],
            "qr": {"points": qr_points, "status": "confirmed", "name": book.name},
        }

    state["current_student"] = None
    return {
        "stage": "done",
        "student": student_brief,
        "book": {"id": str(book.id), "name": book.name},
        "action": "rejected",
        "message": f"{book.name} is already borrowed by someone else",
        "faces": [],
        "qr": {"points": qr_points, "status": "unknown", "name": book.name},
    }


@router.websocket("/ws/recognize")
async def recognize(
    websocket: WebSocket, token: str, db: AsyncSession = Depends(get_db), mode: str = "attendance"
):
    if mode not in VALID_MODES:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        decode_token(token, expected_type="access")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    engine = get_face_engine()
    tracker = FaceTracker()
    qr_detector = cv2.QRCodeDetector()
    library_state: dict = {"current_student": None}

    try:
        while True:
            frame_bytes = await websocket.receive_bytes()
            image = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                continue

            if mode == "library":
                response = await _handle_library_frame(db, image, engine, tracker, qr_detector, library_state)
                await websocket.send_text(json.dumps(response))
                continue

            faces = await asyncio.to_thread(engine.detect, image)
            tracks = tracker.assign([face.bbox for face in faces])
            results = []

            for face, track in zip(faces, tracks, strict=True):
                match = await find_best_match(db, face.embedding)
                matched_student_id = match.student_id if (match and match.is_match) else None
                similarity = match.similarity if match else 0.0

                smoothed = tracker.update_track(track, matched_student_id, similarity)

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
                    elif tracker.already_recorded(track):
                        entry["status"] = "already_marked"
                        entry["name"] = student.name
                    else:
                        marked = await _mark_and_broadcast(
                            db, student, smoothed.similarity, "face", mode=mode
                        )
                        entry["name"] = student.name
                        entry["status"] = "confirmed" if marked else "already_marked"
                        tracker.mark_recorded(track)
                elif matched_student_id:
                    entry["status"] = "recognizing"

                results.append(entry)

            # Mess mode is face-only by design -- no QR fallback, per spec.
            qr_result = await _handle_qr(db, image, qr_detector, mode) if mode == "attendance" else None

            await websocket.send_text(json.dumps({"faces": results, "qr": qr_result}))
    except WebSocketDisconnect:
        pass
    finally:
        pass  # nothing to clean up: tracker/engine are per-connection or process-wide
