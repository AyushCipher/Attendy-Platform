"""Borrow/return logic and the fine formula -- shared by the live library-scan flow
(marks a return the instant it's scanned) and the scheduled overdue job (Milestone 6),
so both compute the exact same number rather than two formulas that could drift.
"""
import datetime
import uuid

from sqlalchemy import select
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
