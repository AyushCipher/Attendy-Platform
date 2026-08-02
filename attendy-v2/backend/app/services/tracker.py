"""Per-connection face tracking + temporal smoothing + a lightweight liveness heuristic.

This is the same shape as the legacy `face_recognition_system.py`'s smoothing design
(track faces across frames, require several consistent recognitions before confirming),
carried over deliberately because it was a genuinely good idea -- it's now fed by
pgvector cosine similarity instead of LBPH distance, and frame-to-frame face-to-track
assignment is a proper Hungarian-algorithm optimal matching (scipy) instead of a
greedy nearest-IoU pick, so two faces close together in frame can't have one steal the
other's track just because it was processed first.

Liveness here is a bbox-motion heuristic (a photo held perfectly still won't show the
natural micro-drift a live face does over ~1-2 seconds) -- explicitly not a production
anti-spoofing model, just enough to block the "hold up a printed photo" case.
"""
from collections import deque
from dataclasses import dataclass, field
from uuid import UUID

import numpy as np
from scipy.optimize import linear_sum_assignment

BBox = tuple[float, float, float, float]

HISTORY_LENGTH = 6
MIN_CONSISTENT_FRAMES = 4
IOU_MATCH_THRESHOLD = 0.3
MIN_MOTION_PX = 3.0  # minimum bbox-center drift across the history window to pass liveness
MAX_UNMATCHED_FRAMES = HISTORY_LENGTH * 2  # a track this stale is a face that left frame


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
    unmatched_frames: int = 0


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

    def assign(self, bboxes: list[BBox]) -> list[_TrackedFace]:
        """Globally-optimal one-to-one assignment of this frame's detected face boxes
        to existing tracks (Hungarian algorithm over an IoU cost matrix), returned in
        the same order as `bboxes`. A detection with no track scoring >= threshold
        (or when there are more detections than tracks) starts a new track. Tracks
        that go unmatched for too many consecutive frames are dropped, so a
        long-running kiosk connection doesn't accumulate stale tracks (and an
        ever-growing cost matrix) for faces that walked away.
        """
        for track in self._tracks:
            track.unmatched_frames += 1

        assigned: dict[int, _TrackedFace] = {}
        if bboxes and self._tracks:
            cost = np.array([[1.0 - _iou(b, t.bbox) for t in self._tracks] for b in bboxes])
            row_idx, col_idx = linear_sum_assignment(cost)
            for r, c in zip(row_idx, col_idx, strict=True):
                if cost[r, c] <= 1.0 - IOU_MATCH_THRESHOLD:
                    track = self._tracks[c]
                    track.bbox = bboxes[r]
                    track.unmatched_frames = 0
                    assigned[r] = track

        results = []
        for i, bbox in enumerate(bboxes):
            if i in assigned:
                results.append(assigned[i])
            else:
                new_track = _TrackedFace(bbox=bbox)
                self._tracks.append(new_track)
                results.append(new_track)

        self._tracks = [t for t in self._tracks if t.unmatched_frames <= MAX_UNMATCHED_FRAMES]
        return results

    def update_track(self, track: _TrackedFace, student_id: UUID | None, similarity: float) -> SmoothedResult:
        track.history.append((student_id, similarity))

        cx, cy = (track.bbox[0] + track.bbox[2]) / 2, (track.bbox[1] + track.bbox[3]) / 2
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

    @staticmethod
    def mark_recorded(track: _TrackedFace) -> None:
        track.already_marked_today = True

    @staticmethod
    def already_recorded(track: _TrackedFace) -> bool:
        return track.already_marked_today

    @staticmethod
    def _passes_liveness(track: _TrackedFace) -> bool:
        if len(track.centers) < HISTORY_LENGTH:
            return False
        xs = [c[0] for c in track.centers]
        ys = [c[1] for c in track.centers]
        drift = (max(xs) - min(xs)) + (max(ys) - min(ys))
        return drift >= MIN_MOTION_PX
