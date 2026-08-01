import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MealRecord(Base):
    """Event log for mid-day-meal tracking: one row per confirmed meal. Mirrors
    AttendanceRecord's shape exactly, but is a separate table -- a student being
    present in class and a student having eaten are independent facts, not the same
    event under a type discriminator.
    """

    __tablename__ = "meal_records"
    __table_args__ = (
        UniqueConstraint("student_id", "event_date", name="uq_meal_student_date"),
        Index("ix_meal_class_section_date", "class_section_id", "event_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_sections.id"), nullable=False
    )

    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[str] = mapped_column(String(16), nullable=False, default="face")
    marked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["Student"] = relationship()  # noqa: F821
    class_section: Mapped["ClassSection"] = relationship()  # noqa: F821
