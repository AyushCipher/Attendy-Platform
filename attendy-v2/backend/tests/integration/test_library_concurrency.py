"""Proves the partial unique index (book_borrows: one open row per book) actually
prevents two concurrent scans of the same book from both creating an open borrow.
The app-level get_open_borrow() check alone can't do this -- two requests can both
read "no open borrow" before either commits -- so this test exercises two independent
DB sessions racing against the real constraint, not a mock.
"""
import asyncio
import uuid

from sqlalchemy import text

from app.db.base import async_session_factory
from app.db.models.book import Book
from app.db.models.student import Student
from app.services.library_service import try_borrow


async def _make_student(class_section_id, roll_number: int) -> Student:
    async with async_session_factory() as session:
        student = Student(name=f"Racer {roll_number}", roll_number=roll_number, class_section_id=class_section_id)
        session.add(student)
        await session.commit()
        await session.refresh(student)
        return student


async def test_concurrent_borrow_of_same_book_only_one_wins(db_session, class_section):
    book = Book(name="Race Condition Test Book", author="Test Author", serial_number=f"RACE-{uuid.uuid4().hex[:8]}")
    db_session.add(book)
    # class_section (fixture) and book are only flush()'d, not committed, by default --
    # the two racer sessions below are independent connections and won't see
    # uncommitted rows under READ COMMITTED, so this test needs a real commit.
    await db_session.commit()

    student_a = await _make_student(class_section.id, roll_number=501)
    student_b = await _make_student(class_section.id, roll_number=502)

    async def attempt(student: Student):
        async with async_session_factory() as session:
            return await try_borrow(session, book.id, student.id, class_section.id)

    result_a, result_b = await asyncio.gather(attempt(student_a), attempt(student_b))

    winners = [r for r in (result_a, result_b) if r is not None]
    losers = [r for r in (result_a, result_b) if r is None]
    assert len(winners) == 1, "exactly one concurrent borrow attempt should have won the race"
    assert len(losers) == 1

    async with async_session_factory() as verify:
        open_count = await verify.scalar(
            text("SELECT count(*) FROM book_borrows WHERE book_id = :id AND returned_at IS NULL"),
            {"id": book.id},
        )
        assert open_count == 1, "the DB must never end up with two open borrows for the same book"

    async with async_session_factory() as cleanup:
        await cleanup.execute(text("DELETE FROM book_borrows WHERE book_id = :id"), {"id": book.id})
        await cleanup.execute(text("DELETE FROM books WHERE id = :id"), {"id": book.id})
        await cleanup.execute(text("DELETE FROM students WHERE id IN (:a, :b)"), {"a": student_a.id, "b": student_b.id})
        await cleanup.commit()
