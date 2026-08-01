"""Per-connection face tracking + temporal smoothing + a lightweight liveness heuristic.

This is the same shape as the legacy `face_recognition_system.py`'s smoothing design
(track faces across frames, require several consistent recognitions before confirming),
carried over deliberately because it was a genuinely good idea -- it's now fed by
pgvector cosine similarity instead of LBPH distance, and face-tracking uses IoU instead
of raw center-proximity (more robust to head movement).

Liveness here is a bbox-motion heuristic (a photo held perfectly still won't show the
natural micro-drift a live face does over ~1-2 seconds) -- explicitly not a production
anti-spoofing model, just enough to block the "hold up a printed photo" case.
"""
from collections import deque
from dataclasses import dataclass, field
from uuid import UUID

BBox = tuple[float, float, float, float]

HISTORY_LENGTH = 8
MIN_CONSISTENT_FRAMES = 5
IOU_MATCH_THRESHOLD = 0.3
MIN_MOTION_PX = 3.0  # minimum bbox-center drift across the history window to pass liveness


def _iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


@dataclass
class _TrackedFace:
    bbox: BBox
    history: deque[tuple[UUID | None, float]] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    centers: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    already_marked_today: bool = False


@dataclass
class SmoothedResult:
    student_id: UUID | None
    similarity: float
    confirmed: bool
    live: bool


class FaceTracker:
    """One instance per open /ws/recognize connection."""

    def __init__(self) -> None:
        self._tracks: list[_TrackedFace] = []

    def _find_or_create_track(self, bbox: BBox) -> _TrackedFace:
        best_track, best_iou = None, 0.0
        for track in self._tracks:
            score = _iou(track.bbox, bbox)
            if score > best_iou:
                best_track, best_iou = track, score

        if best_track is not None and best_iou >= IOU_MATCH_THRESHOLD:
            best_track.bbox = bbox
            return best_track

        new_track = _TrackedFace(bbox=bbox)
        self._tracks.append(new_track)
        return new_track

    def update(self, bbox: BBox, student_id: UUID | None, similarity: float) -> SmoothedResult:
        track = self._find_or_create_track(bbox)
        track.history.append((student_id, similarity))

        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        track.centers.append((cx, cy))

        counts: dict[UUID | None, list[float]] = {}
        for sid, sim in track.history:
            counts.setdefault(sid, []).append(sim)

        best_id, best_count, best_avg = None, 0, 0.0
        for sid, sims in counts.items():
            if sid is None:
                continue
            count, avg = len(sims), sum(sims) / len(sims)
            if count > best_count:
                best_id, best_count, best_avg = sid, count, avg

        confirmed = best_id is not None and best_count >= MIN_CONSISTENT_FRAMES
        live = self._passes_liveness(track)

        return SmoothedResult(
            student_id=best_id if confirmed else None,
            similarity=best_avg,
            confirmed=confirmed and live,
            live=live,
        )

    def mark_recorded(self, student_id: UUID) -> None:
        for track in self._tracks:
            if track.history and track.history[-1][0] == student_id:
                track.already_marked_today = True

    def already_recorded(self, bbox: BBox) -> bool:
        track = self._find_or_create_track(bbox)
        return track.already_marked_today

    @staticmethod
    def _passes_liveness(track: _TrackedFace) -> bool:
        if len(track.centers) < HISTORY_LENGTH:
            return False
        xs = [c[0] for c in track.centers]
        ys = [c[1] for c in track.centers]
        drift = (max(xs) - min(xs)) + (max(ys) - min(ys))
        return drift >= MIN_MOTION_PX
