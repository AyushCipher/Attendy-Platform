import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("roll_number", "class_section_id", name="uq_students_roll_class_section"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    roll_number: Mapped[int] = mapped_column(Integer, nullable=False)
    class_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_sections.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    class_section: Mapped["ClassSection"] = relationship(back_populates="students")  # noqa: F821
    face_embeddings: Mapped[list["FaceEmbedding"]] = relationship(  # noqa: F821
        back_populates="student", cascade="all, delete-orphan"
    )
