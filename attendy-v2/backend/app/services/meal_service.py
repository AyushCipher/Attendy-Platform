import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meal import MealRecord


async def mark_meal_if_new(
    db: AsyncSession,
    student_id: UUID,
    class_section_id: UUID,
    source: str = "face",
    marked_by: UUID | None = None,
) -> MealRecord | None:
    """Mirrors attendance_service.mark_present_if_new exactly, against meal_records
    instead. Kept as its own small function rather than a generic parameterized
    version shared with attendance -- only two call sites, and this project's
    convention is not to abstract prematurely for that few consumers.
    """
    today = datetime.date.today()

    stmt = (
        insert(MealRecord)
        .values(
            student_id=student_id,
            class_section_id=class_section_id,
            source=source,
            marked_by=marked_by,
            event_date=today,
        )
        .on_conflict_do_nothing(constraint="uq_meal_student_date")
        .returning(MealRecord)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.first()
    return row[0] if row else None
