"""Stores one representative photo per student, captured from their first usable
enrollment image. Saved to local disk (a persistent volume backs this in Docker,
matching how the rest of this app is deployed) rather than a DB column -- this
mirrors the same on-demand-serving pattern already used for QR codes.
"""
import uuid
from pathlib import Path

import cv2
import numpy as np

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "students"
PHOTO_MAX_DIM = 480


def save_student_photo(student_id: uuid.UUID, image: np.ndarray) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    h, w = image.shape[:2]
    scale = PHOTO_MAX_DIM / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    cv2.imwrite(str(UPLOAD_DIR / f"{student_id}.jpg"), image)


def load_student_photo(student_id: uuid.UUID) -> bytes | None:
    path = UPLOAD_DIR / f"{student_id}.jpg"
    if not path.exists():
        return None
    return path.read_bytes()
