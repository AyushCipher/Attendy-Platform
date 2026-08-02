"""Borrow/return logic and the fine formula -- shared by the live library-scan flow
(marks a return the instant it's scanned) and the scheduled overdue job (Milestone 6),
so both compute the exact same number rather than two formulas that could drift.
"""
import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_borrow import BookBorrow

GRACE_DAYS = 7
FINE_PER_PERIOD = 100


def compute_fine(borrowed_at: datetime.datetime, now: datetime.datetime) -> int:
    """(days since borrow // 7) * 100, floored at 0. Recomputes to the correct
    value rather than incrementing, so calling this repeatedly (e.g. a daily job)
    is always safe -- it can never double-charge.
    """
    days_elapsed = (now - borrowed_at).days
    if days_elapsed < GRACE_DAYS:
        return 0
    return (days_elapsed // GRACE_DAYS) * FINE_PER_PERIOD


async def get_open_borrow(db: AsyncSession, book_id: uuid.UUID) -> BookBorrow | None:
    return await db.scalar(
        select(BookBorrow).where(BookBorrow.book_id == book_id, BookBorrow.returned_at.is_(None))
    )


async def try_borrow(
    db: AsyncSession, book_id: uuid.UUID, student_id: uuid.UUID, class_section_id: uuid.UUID
) -> BookBorrow | None:
    """Attempts to open a new borrow, returning None if another open borrow for this
    book won a race instead.

    Callers are expected to have already checked get_open_borrow() for the normal
    (non-racing) case -- that check just produces a better UX message before
    attempting the insert. The actual guarantee against two concurrent scans of the
    same book both creating an open borrow comes from the DB-level partial unique
    index (book_borrows.uq_book_borrows_one_open_per_book, one open row per book),
    not from that check: two requests can both pass get_open_borrow() before either
    commits, so only a DB constraint -- not an app-level check-then-insert -- can
    actually prevent the double-borrow.
    """
    borrow = BookBorrow(book_id=book_id, student_id=student_id, class_section_id=class_section_id)
    db.add(borrow)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(borrow)
    return borrow
