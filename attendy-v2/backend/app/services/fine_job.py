"""Daily overdue-fine recomputation. Runs via APScheduler (wired in app/main.py's
lifespan). Recomputes each open borrow's fine to what it should currently be
(app.services.library_service.compute_fine) rather than incrementing, so firing
this job more than once in a day -- or re-running it after a missed day -- can
never double-charge a student.
"""
import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_borrow import BookBorrow
from app.services.library_service import compute_fine

logger = logging.getLogger(__name__)


async def apply_overdue_fines(db: AsyncSession) -> int:
    """Returns the number of borrows whose fine_amount was updated."""
    now = datetime.datetime.now(datetime.timezone.utc)
    open_borrows = (
        await db.execute(select(BookBorrow).where(BookBorrow.returned_at.is_(None)))
    ).scalars().all()

    updated = 0
    for borrow in open_borrows:
        expected = compute_fine(borrow.borrowed_at, now)
        if expected > borrow.fine_amount:
            borrow.fine_amount = expected
            updated += 1

    if updated:
        await db.commit()
    logger.info("apply_overdue_fines: checked %d open borrows, updated %d", len(open_borrows), updated)
    return updated
