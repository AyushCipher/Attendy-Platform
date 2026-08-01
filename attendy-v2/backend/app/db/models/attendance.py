import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AttendanceRecord(Base):
    """Event log: one row per confirmed presence. Absence = no row for that student+date."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "event_date", name="uq_attendance_student_date"),
        Index("ix_attendance_class_section_date", "class_section_id", "event_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized snapshot: a student moving class next year must not rewrite past attendance.
    class_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_sections.id"), nullable=False
    )

    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="face")
    marked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped["Student"] = relationship()  # noqa: F821
    class_section: Mapped["ClassSection"] = relationship()  # noqa: F821
