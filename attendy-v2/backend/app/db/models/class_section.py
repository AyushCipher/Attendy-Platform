import uuid

from sqlalchemy import SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClassSection(Base):
    __tablename__ = "class_sections"
    __table_args__ = (UniqueConstraint("grade", "section", name="uq_class_sections_grade_section"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    section: Mapped[str] = mapped_column(String(4), nullable=False)

    students: Mapped[list["Student"]] = relationship(back_populates="class_section")  # noqa: F821

    @property
    def label(self) -> str:
        return f"Class {self.grade}-{self.section}"
