import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.attendance import AttendanceRecord
from app.db.models.student import Student


def _school_days(date_from: datetime.date, date_to: datetime.date) -> list[datetime.date]:
    """Weekdays only (Mon-Fri) -- a real school has no Sat/Sun classes."""
    days = []
    current = date_from
    while current <= date_to:
        if current.weekday() < 5:
            days.append(current)
        current += datetime.timedelta(days=1)
    return days


async def get_daily_summary(
    db: AsyncSession,
    date_from: datetime.date,
    date_to: datetime.date,
    class_section_id: uuid.UUID | None,
) -> tuple[list[tuple[datetime.date, int, int]], int]:
    """Returns [(date, present_count, total_students)] for each school day, plus total_students."""
    student_query = select(func.count()).select_from(Student).where(Student.status == "active")
    if class_section_id is not None:
        student_query = student_query.where(Student.class_section_id == class_section_id)
    total_students = (await db.execute(student_query)).scalar_one()

    present_query = (
        select(AttendanceRecord.event_date, func.count(func.distinct(AttendanceRecord.student_id)))
        .join(Student, Student.id == AttendanceRecord.student_id)
        .where(AttendanceRecord.event_date.between(date_from, date_to))
        .where(Student.status == "active")
        .group_by(AttendanceRecord.event_date)
    )
    if class_section_id is not None:
        present_query = present_query.where(Student.class_section_id == class_section_id)

    present_by_date = dict((await db.execute(present_query)).all())

    points = [
        (day, present_by_date.get(day, 0), total_students) for day in _school_days(date_from, date_to)
    ]
    return points, total_students


async def get_chronic_absentees(
    db: AsyncSession,
    date_from: datetime.date,
    date_to: datetime.date,
    threshold: float,
    class_section_id: uuid.UUID | None,
):
    school_days = _school_days(date_from, date_to)
    school_days_set = set(school_days)
    total_days = len(school_days)
    if total_days == 0:
        return []

    # Count in Python, not SQL: a record landing on a weekend (e.g. a manual backfill)
    # must not count toward presence, since the denominator (total_days) excludes it.
    raw_dates_query = select(AttendanceRecord.student_id, AttendanceRecord.event_date).where(
        AttendanceRecord.event_date.between(date_from, date_to)
    )
    present_counts: dict[uuid.UUID, int] = {}
    for student_id, event_date in (await db.execute(raw_dates_query)).all():
        if event_date in school_days_set:
            present_counts[student_id] = present_counts.get(student_id, 0) + 1

    students_query = select(Student).where(Student.status == "active")
    if class_section_id is not None:
        students_query = students_query.where(Student.class_section_id == class_section_id)
    students_query = students_query.options(selectinload(Student.class_section))
    students = (await db.execute(students_query)).scalars().all()

    results = []
    for student in students:
        present_days = present_counts.get(student.id, 0)
        absent_days = total_days - present_days
        absence_rate = absent_days / total_days
        if absence_rate >= threshold:
            results.append((student, absent_days, absence_rate))

    results.sort(key=lambda r: r[2], reverse=True)
    return [
        {
            "student": student,
            "absent_days": absent_days,
            "absence_rate": absence_rate,
            "school_days": total_days,
        }
        for student, absent_days, absence_rate in results
    ]
