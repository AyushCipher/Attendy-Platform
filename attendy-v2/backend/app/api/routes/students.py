import asyncio
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models.class_section import ClassSection
from app.db.models.face_embedding import FaceEmbedding
from app.db.models.student import Student
from app.schemas.class_section import ClassSectionOut
from app.schemas.student import (
    FaceEnrollResult,
    StudentCreate,
    StudentListResponse,
    StudentOut,
    StudentUpdate,
)
from app.services.face_engine import get_face_engine
from app.services.photo_service import load_student_photo, save_student_photo
from app.services.qr_service import build_qr_png

router = APIRouter(prefix="/students", tags=["students"], dependencies=[Depends(get_current_admin)])

MIN_DET_SCORE = 0.5


def _to_student_out(student: Student, face_enrolled: bool) -> StudentOut:
    return StudentOut(
        id=student.id,
        name=student.name,
        roll_number=student.roll_number,
        status=student.status,
        photo_url=student.photo_url,
        class_section=ClassSectionOut.model_validate(student.class_section),
        face_enrolled=face_enrolled,
        created_at=student.created_at,
    )


@router.get("", response_model=StudentListResponse)
async def list_students(
    class_section_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    face_enrolled_expr = exists().where(FaceEmbedding.student_id == Student.id)

    query = select(Student, face_enrolled_expr.label("face_enrolled")).options(
        selectinload(Student.class_section)
    )

    if class_section_id is not None:
        query = query.where(Student.class_section_id == class_section_id)
    if status_filter is not None:
        query = query.where(Student.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Student.name.ilike(like), Student.roll_number.cast(str).ilike(like)))

    count_query = select(func.count()).select_from(query.with_only_columns(Student.id).subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(Student.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(query)).all()

    items = [_to_student_out(student, face_enrolled) for student, face_enrolled in rows]
    return StudentListResponse(items=items, total=total, page=page, page_size=page_size)


async def _get_or_create_class_section(db: AsyncSession, grade: int, section: str) -> ClassSection:
    existing = await db.scalar(
        select(ClassSection).where(ClassSection.grade == grade, ClassSection.section == section)
    )
    if existing is not None:
        return existing

    class_section = ClassSection(grade=grade, section=section)
    db.add(class_section)
    try:
        await db.flush()
    except IntegrityError:
        # Lost a race with a concurrent request creating the same (grade, section).
        await db.rollback()
        class_section = await db.scalar(
            select(ClassSection).where(ClassSection.grade == grade, ClassSection.section == section)
        )
    return class_section


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    class_section = await _get_or_create_class_section(db, payload.grade, payload.section)

    student = Student(
        name=payload.name,
        roll_number=payload.roll_number,
        class_section_id=class_section.id,
    )
    db.add(student)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This roll number already exists in this class/section"
        ) from exc

    await db.refresh(student, attribute_names=["class_section"])
    return _to_student_out(student, face_enrolled=False)


@router.get("/{student_id}/qr-code")
async def get_student_qr_code(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    student = await _get_student_or_404(student_id, db)
    png_bytes = build_qr_png(student.id)
    return Response(content=png_bytes, media_type="image/png")


@router.get("/{student_id}/photo")
async def get_student_photo(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_student_or_404(student_id, db)
    photo_bytes = load_student_photo(student_id)
    if photo_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo on file for this student")
    return Response(content=photo_bytes, media_type="image/jpeg")


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    student = await _get_student_or_404(student_id, db)
    face_enrolled = await db.scalar(
        select(exists().where(FaceEmbedding.student_id == student_id))
    )
    return _to_student_out(student, bool(face_enrolled))


@router.patch("/{student_id}", response_model=StudentOut)
async def update_student(student_id: uuid.UUID, payload: StudentUpdate, db: AsyncSession = Depends(get_db)):
    student = await _get_student_or_404(student_id, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This roll number already exists in this class/section"
        ) from exc

    await db.refresh(student, attribute_names=["class_section"])
    face_enrolled = await db.scalar(
        select(exists().where(FaceEmbedding.student_id == student_id))
    )
    return _to_student_out(student, bool(face_enrolled))


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    student = await _get_student_or_404(student_id, db)
    student.status = "inactive"  # soft delete
    await db.commit()


@router.post("/{student_id}/enroll-face", response_model=FaceEnrollResult)
async def enroll_face(
    student_id: uuid.UUID,
    photos: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_student_or_404(student_id, db)
    engine = get_face_engine()

    usable = 0
    quality_scores: list[float] = []
    rejected_reasons: list[str] = []
    photo_saved = False

    for photo in photos:
        raw = await photo.read()
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            rejected_reasons.append(f"{photo.filename}: not a valid image")
            continue

        faces = await asyncio.to_thread(engine.detect, image)
        if not faces:
            rejected_reasons.append(f"{photo.filename}: no face detected")
            continue

        best = max(faces, key=lambda f: f.det_score)
        if best.det_score < MIN_DET_SCORE:
            rejected_reasons.append(f"{photo.filename}: face detection too uncertain")
            continue

        db.add(
            FaceEmbedding(
                student_id=student.id,
                embedding=best.embedding.tolist(),
                quality_score=best.det_score,
                source="enrollment",
            )
        )
        usable += 1
        quality_scores.append(best.det_score)

        if not photo_saved:
            # The first usable capture of this enrollment session becomes the
            # student's representative photo -- a re-enrollment naturally refreshes
            # it, which is the expected behavior.
            await asyncio.to_thread(save_student_photo, student.id, image)
            photo_saved = True

    if photo_saved:
        student.photo_url = "available"
    await db.commit()

    total = await db.scalar(
        select(func.count()).select_from(FaceEmbedding).where(FaceEmbedding.student_id == student_id)
    )

    return FaceEnrollResult(
        images_received=len(photos),
        images_usable=usable,
        average_quality=sum(quality_scores) / len(quality_scores) if quality_scores else None,
        rejected_reasons=rejected_reasons,
        total_embeddings_stored=total or 0,
    )


@router.delete("/{student_id}/face-embeddings", status_code=status.HTTP_204_NO_CONTENT)
async def clear_face_embeddings(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_student_or_404(student_id, db)
    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.student_id == student_id))
    await db.commit()


async def _get_student_or_404(student_id: uuid.UUID, db: AsyncSession) -> Student:
    query = select(Student).where(Student.id == student_id).options(selectinload(Student.class_section))
    student = (await db.execute(query)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student
