"""Wraps InsightFace's FaceAnalysis: face detection + 512-d ArcFace embedding extraction.

This replaces the legacy OpenCV LBPH pipeline (face_recognition_system.py in Attendy-main),
which failed because enrollment and live recognition used different Haar-cascade parameters
and typically trained on 1-3 static photos. ArcFace is a fixed pretrained model (no training
step), and detection is the same SCRFD detector at both enrollment and recognition time,
so that class of train/live mismatch can't happen here by construction.
"""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from insightface.app import FaceAnalysis

from app.core.config import get_settings

EMBEDDING_DIM = 512


@dataclass
class DetectedFace:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    embedding: np.ndarray  # shape (512,), NOT L2-normalized by insightface by default
    det_score: float
    landmarks: np.ndarray  # 5-point landmarks (left eye, right eye, nose, mouth L, mouth R)


class FaceEngine:
    def __init__(self, model_pack: str) -> None:
        self._app = FaceAnalysis(name=model_pack, providers=["CPUExecutionProvider"])
        self._app.prepare(ctx_id=0, det_size=(640, 640))

    def detect(self, bgr_image: np.ndarray) -> list[DetectedFace]:
        faces = self._app.get(bgr_image)
        results = []
        for face in faces:
            embedding = face.normed_embedding  # already L2-normalized -> dot product == cosine sim
            results.append(
                DetectedFace(
                    bbox=tuple(face.bbox.tolist()),
                    embedding=embedding.astype(np.float32),
                    det_score=float(face.det_score),
                    landmarks=face.kps,
                )
            )
        return results


@lru_cache
def get_face_engine() -> FaceEngine:
    settings = get_settings()
    return FaceEngine(model_pack=settings.face_model_pack)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))
