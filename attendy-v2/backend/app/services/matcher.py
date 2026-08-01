"""pgvector-backed nearest-embedding lookup, used by the recognition WS handler (Phase 5)."""
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models.face_embedding import FaceEmbedding
from app.db.models.student import Student

settings = get_settings()


@dataclass
class MatchResult:
    student_id: UUID
    similarity: float
    is_match: bool


async def find_best_match(db: AsyncSession, embedding: np.ndarray) -> MatchResult | None:
    """Cosine distance search via pgvector's `<=>` operator.

    embedding is expected L2-normalized (as FaceEngine.detect returns), so
    cosine_similarity = 1 - cosine_distance.
    """
    distance = FaceEmbedding.embedding.cosine_distance(embedding.tolist())
    query = (
        select(FaceEmbedding.student_id, distance.label("distance"))
        .order_by(distance)
        .limit(1)
    )
    row = (await db.execute(query)).first()
    if row is None:
        return None

    similarity = 1 - row.distance
    return MatchResult(
        student_id=row.student_id,
        similarity=similarity,
        is_match=similarity >= settings.face_match_threshold,
    )


async def get_student_if_active(db: AsyncSession, student_id: UUID) -> Student | None:
    student = await db.get(Student, student_id, options=[selectinload(Student.class_section)])
    if student is not None and student.status == "active":
        return student
    return None
