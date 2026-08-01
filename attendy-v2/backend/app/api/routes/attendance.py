import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models.admin import Admin
from app.db.models.attendance import AttendanceRecord
from app.db.models.meal import MealRecord
from app.db.models.student import Student
from app.schemas.attendance import (
    AttendanceRow,
    AttendanceSheetResponse,
    AttendanceSummaryResponse,
    ChronicAbsenteeRow,
    ChronicAbsenteesResponse,
    DailySummaryPoint,
    ManualAttendanceRequest,
)
from app.schemas.class_section import ClassSectionOut
from app.schemas.meal import MealRow, MealSheetResponse
from app.services import analytics_service
from app.services.attendance_service import mark_present_if_new
from app.services.export_service import build_attendance_workbook

router = APIRouter(prefix="/attendance", tags=["attendance"], dependencies=[Depends(get_current_admin)])


def _build_sheet_query(event_date: datetime.date, class_section_id: uuid.UUID | None, search: str | None):
    query = (
        select(Student, AttendanceRecord)
        .outerjoin(
            AttendanceRecord,
            (AttendanceRecord.student_id == Student.id) & (AttendanceRecord.event_date == event_date),
        )
        .where(Student.status == "active")
        .options(selectinload(Student.class_section))
    )
    if class_section_id is not None:
        query = query.where(Student.class_section_id == class_section_id)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Student.name.ilike(like), Student.roll_number.cast(str).ilike(like)))
    return query


@router.get("", response_model=AttendanceSheetResponse)
async def get_attendance_sheet(
    event_date: datetime.date = Query(default_factory=datetime.date.today),
    class_section_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = _build_sheet_query(event_date, class_section_id, search)
    rows = (await db.execute(query.order_by(Student.name))).all()

    items: list[AttendanceRow] = []
    present_count = 0
    for student, record in rows:
        is_present = record is not None
        if is_present:
            present_count += 1
        row_status = "present" if is_present else "absent"
        if status_filter and status_filter != row_status:
            continue
        items.append(
            AttendanceRow(
                student_id=student.id,
                name=student.name,
                roll_number=student.roll_number,
                class_section=ClassSectionOut.model_validate(student.class_section),
                status=row_status,
                event_time=record.event_time if record else None,
                confidence=record.confidence if record else None,
                source=record.source if record else None,
            )
        )

    total_students = len(rows)
    return AttendanceSheetResponse(
        date=event_date,
        items=items,
        total=total_students,
        present_count=present_count,
        absent_count=total_students - present_count,
    )


@router.get("/meals", response_model=MealSheetResponse)
async def get_meal_sheet(
    event_date: datetime.date = Query(default_factory=datetime.date.today),
    class_section_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mirrors get_attendance_sheet's filters/shape exactly, reading meal_records
    instead -- kept as its own route rather than a generic table-parameterized one,
    same reasoning as mark_meal_if_new alongside mark_present_if_new.
    """
    query = (
        select(Student, MealRecord)
        .outerjoin(
            MealRecord,
            (MealRecord.student_id == Student.id) & (MealRecord.event_date == event_date),
        )
        .where(Student.status == "active")
        .options(selectinload(Student.class_section))
    )
    if class_section_id is not None:
        query = query.where(Student.class_section_id == class_section_id)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Student.name.ilike(like), Student.roll_number.cast(str).ilike(like)))

    rows = (await db.execute(query.order_by(Student.name))).all()

    items: list[MealRow] = []
    present_count = 0
    for student, record in rows:
        is_present = record is not None
        if is_present:
            present_count += 1
        row_status = "present" if is_present else "absent"
        if status_filter and status_filter != row_status:
            continue
        items.append(
            MealRow(
                student_id=student.id,
                name=student.name,
                roll_number=student.roll_number,
                class_section=ClassSectionOut.model_validate(student.class_section),
                status=row_status,
                event_time=record.event_time if record else None,
                source=record.source if record else None,
            )
        )

    total_students = len(rows)
    return MealSheetResponse(
        date=event_date,
        items=items,
        total=total_students,
        present_count=present_count,
        absent_count=total_students - present_count,
    )


@router.post("/manual", response_model=AttendanceRow)
async def mark_manual_attendance(
    payload: ManualAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    student = await db.get(Student, payload.student_id, options=[selectinload(Student.class_section)])
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")

    if payload.status == "present":
        if payload.event_date == datetime.date.today():
            record = await mark_present_if_new(
                db,
                student_id=student.id,
                class_section_id=student.class_section_id,
                confidence=None,
                source="manual",
                marked_by=admin.id,
            )
        else:
            # Backfilling a past date bypasses the ON CONFLICT DO NOTHING happy path
            # used for live scans, since that helper always stamps "today".
            existing = await db.scalar(
                select(AttendanceRecord).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.event_date == payload.event_date,
                )
            )
            if existing is None:
                record = AttendanceRecord(
                    student_id=student.id,
                    class_section_id=student.class_section_id,
                    event_date=payload.event_date,
                    source="manual",
                    marked_by=admin.id,
                )
                db.add(record)
                await db.commit()
            else:
                record = existing
    else:
        await db.execute(
            AttendanceRecord.__table__.delete().where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.event_date == payload.event_date,
            )
        )
        await db.commit()
        record = None

    return AttendanceRow(
        student_id=student.id,
        name=student.name,
        roll_number=student.roll_number,
        class_section=ClassSectionOut.model_validate(student.class_section),
        status=payload.status,
        event_time=record.event_time if record else None,
        confidence=record.confidence if record else None,
        source=record.source if record else None,
    )


@router.get("/export")
async def export_attendance_sheet(
    event_date: datetime.date = Query(default_factory=datetime.date.today),
    class_section_id: uuid.UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    sheet = await get_attendance_sheet(event_date, class_section_id, status_filter, search, db)
    workbook_bytes = build_attendance_workbook(str(event_date), sheet.items)
    return Response(
        content=workbook_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="attendance_{event_date}.xlsx"'},
    )


@router.get("/analytics/summary", response_model=AttendanceSummaryResponse)
async def get_attendance_summary(
    date_from: datetime.date,
    date_to: datetime.date,
    class_section_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if date_from > date_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from must be on or before date_to")

    points, total_students = await analytics_service.get_daily_summary(db, date_from, date_to, class_section_id)

    total_present = sum(p for _, p, _ in points)
    total_possible = sum(t for _, _, t in points)
    overall_rate = (total_present / total_possible) if total_possible else 0.0

    return AttendanceSummaryResponse(
        date_from=date_from,
        date_to=date_to,
        points=[
            DailySummaryPoint(date=day, present_count=present, absent_count=total - present, total=total)
            for day, present, total in points
        ],
        overall_present_rate=round(overall_rate, 4),
    )


@router.get("/analytics/chronic-absentees", response_model=ChronicAbsenteesResponse)
async def get_chronic_absentees(
    date_from: datetime.date,
    date_to: datetime.date,
    threshold: float = Query(default=0.2, ge=0, le=1),
    class_section_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if date_from > date_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from must be on or before date_to")

    rows = await analytics_service.get_chronic_absentees(db, date_from, date_to, threshold, class_section_id)

    return ChronicAbsenteesResponse(
        date_from=date_from,
        date_to=date_to,
        threshold=threshold,
        items=[
            ChronicAbsenteeRow(
                student_id=row["student"].id,
                name=row["student"].name,
                roll_number=row["student"].roll_number,
                class_section=ClassSectionOut.model_validate(row["student"].class_section),
                school_days=row["school_days"],
                absent_days=row["absent_days"],
                absence_rate=round(row["absence_rate"], 4),
            )
            for row in rows
        ],
    )
