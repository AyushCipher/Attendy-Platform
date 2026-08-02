import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BookBorrow(Base):
    """One row per borrow. An open borrow (returned_at IS NULL) is what makes a book
    currently unavailable -- see Book's docstring. fine_amount is recomputed (not
    incremented) by the overdue-fines job, so re-running it is always safe. Per the
    user's explicit choice, returning a book never clears fine_amount -- only
    settle-fine (fine_settled) does, as a separate admin action.

    The partial unique index below (one open borrow per book) is load-bearing, not
    just an optimization: the library-scan flow reads "is this book open?" and then
    inserts a new borrow as two separate statements, so without a DB-level guard two
    concurrent scans of the same book could both pass the read before either commits
    and create two open borrows for one book. See library_service.try_borrow, which
    relies on this index to make that insert atomic instead of racy.
    """

    __tablename__ = "book_borrows"
    __table_args__ = (
        Index(
            "uq_book_borrows_one_open_per_book",
            "book_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_sections.id"), nullable=False
    )

    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fine_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fine_settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    book: Mapped["Book"] = relationship()  # noqa: F821
    student: Mapped["Student"] = relationship()  # noqa: F821
    class_section: Mapped["ClassSection"] = relationship()  # noqa: F821
