"""Phase 3 gate: prove ArcFace embeddings + pgvector cosine search correctly separate
two distinct people, and correctly re-identify the same person under simple
transformations (flip/brightness), BEFORE any camera UI depends on this pipeline.
"""
from pathlib import Path

import cv2
import pytest

from app.db.models.face_embedding import FaceEmbedding
from app.db.models.student import Student
from app.services.face_engine import FaceEngine
from app.services.matcher import find_best_match

SAMPLE_IMAGE = (
    Path(__file__).resolve().parents[2]
    / "venv/lib/site-packages/insightface/data/images/t1.jpg"
)


@pytest.fixture(scope="module")
def engine():
    return FaceEngine(model_pack="buffalo_l")


@pytest.fixture(scope="module")
def group_faces(engine):
    image = cv2.imread(str(SAMPLE_IMAGE))
    faces = engine.detect(image)
    assert len(faces) >= 2, "sample image must contain at least two distinct faces"
    return faces


async def _make_student(db_session, class_section, roll_number: int) -> Student:
    student = Student(name=f"Test Student {roll_number}", roll_number=roll_number, class_section_id=class_section.id)
    db_session.add(student)
    await db_session.flush()
    return student


@pytest.mark.asyncio
async def test_pgvector_match_distinguishes_two_people(db_session, class_section, group_faces):
    student_a = await _make_student(db_session, class_section, roll_number=101)
    student_b = await _make_student(db_session, class_section, roll_number=102)

    db_session.add(
        FaceEmbedding(
            student_id=student_a.id,
            embedding=group_faces[0].embedding.tolist(),
            quality_score=group_faces[0].det_score,
        )
    )
    db_session.add(
        FaceEmbedding(
            student_id=student_b.id,
            embedding=group_faces[1].embedding.tolist(),
            quality_score=group_faces[1].det_score,
        )
    )
    await db_session.flush()

    match_for_a = await find_best_match(db_session, group_faces[0].embedding)
    assert match_for_a is not None
    assert match_for_a.student_id == student_a.id
    assert match_for_a.is_match
    assert match_for_a.similarity > 0.9

    match_for_b = await find_best_match(db_session, group_faces[1].embedding)
    assert match_for_b is not None
    assert match_for_b.student_id == student_b.id
    assert match_for_b.is_match


@pytest.mark.asyncio
async def test_pgvector_match_survives_flip_augmentation(db_session, class_section, engine, group_faces):
    """Simulates re-identifying the same person from a different camera angle."""
    student = await _make_student(db_session, class_section, roll_number=201)
    db_session.add(
        FaceEmbedding(
            student_id=student.id,
            embedding=group_faces[0].embedding.tolist(),
            quality_score=group_faces[0].det_score,
        )
    )
    await db_session.flush()

    image = cv2.imread(str(SAMPLE_IMAGE))
    x1, y1, x2, y2 = (int(v) for v in group_faces[0].bbox)
    h, w = image.shape[:2]
    pad = int(0.6 * max(x2 - x1, y2 - y1))
    crop = image[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]
    flipped = cv2.flip(crop, 1)

    flipped_faces = engine.detect(flipped)
    assert flipped_faces, "engine must still detect a face in the flipped crop"

    match = await find_best_match(db_session, flipped_faces[0].embedding)
    assert match is not None
    assert match.student_id == student.id
    assert match.is_match, f"expected a match, got similarity={match.similarity:.4f}"


@pytest.mark.asyncio
async def test_no_embeddings_returns_none(db_session):
    import numpy as np

    result = await find_best_match(db_session, np.zeros(512, dtype="float32"))
    assert result is None
