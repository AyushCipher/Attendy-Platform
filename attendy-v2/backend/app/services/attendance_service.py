import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attendance import AttendanceRecord


async def mark_present_if_new(
    db: AsyncSession,
    student_id: UUID,
    class_section_id: UUID,
    confidence: float | None,
    source: str = "face",
    marked_by: UUID | None = None,
) -> AttendanceRecord | None:
    """Insert today's attendance row for this student. Returns the row if this call
    was the one that created it, or None if the student was already marked today
    (UNIQUE(student_id, event_date) makes this a safe no-op under concurrent frames).
    """
    today = datetime.date.today()

    stmt = (
        insert(AttendanceRecord)
        .values(
            student_id=student_id,
            class_section_id=class_section_id,
            event_date=today,
            confidence=confidence,
            source=source,
            marked_by=marked_by,
        )
        .on_conflict_do_nothing(constraint="uq_attendance_student_date")
        .returning(AttendanceRecord)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.first()
    return row[0] if row else None
