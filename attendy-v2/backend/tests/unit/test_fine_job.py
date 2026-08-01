"""Fine formula + scheduled-job regression tests. Uses backdated fixture data and
calls the job function directly rather than waiting on real wall-clock time.
"""
import datetime

import pytest

from app.db.models.book import Book
from app.db.models.book_borrow import BookBorrow
from app.db.models.student import Student
from app.services.fine_job import apply_overdue_fines
from app.services.library_service import compute_fine


def test_compute_fine_formula():
    now = datetime.datetime(2026, 1, 22, tzinfo=datetime.timezone.utc)

    assert compute_fine(now - datetime.timedelta(days=6), now) == 0  # within grace period
    assert compute_fine(now - datetime.timedelta(days=7), now) == 100
    assert compute_fine(now - datetime.timedelta(days=13), now) == 100
    assert compute_fine(now - datetime.timedelta(days=14), now) == 200
    assert compute_fine(now - datetime.timedelta(days=21), now) == 300


@pytest.mark.asyncio
async def test_apply_overdue_fines_updates_open_borrows_only(db_session, class_section):
    now = datetime.datetime.now(datetime.timezone.utc)

    student = Student(name="Fine Test Student", roll_number=555, class_section_id=class_section.id)
    db_session.add(student)
    await db_session.flush()

    overdue_book = Book(name="Overdue Book", author="A", serial_number=f"FINE-{class_section.section}-1")
    returned_book = Book(name="Returned Book", author="A", serial_number=f"FINE-{class_section.section}-2")
    on_time_book = Book(name="On Time Book", author="A", serial_number=f"FINE-{class_section.section}-3")
    db_session.add_all([overdue_book, returned_book, on_time_book])
    await db_session.flush()

    overdue_borrow = BookBorrow(
        book_id=overdue_book.id,
        student_id=student.id,
        class_section_id=class_section.id,
        borrowed_at=now - datetime.timedelta(days=15),
    )
    # Already returned -- the job must not touch this even though it was late,
    # since fine_amount for a closed borrow is fixed at return time, not recomputed
    # daily.
    already_returned_borrow = BookBorrow(
        book_id=returned_book.id,
        student_id=student.id,
        class_section_id=class_section.id,
        borrowed_at=now - datetime.timedelta(days=20),
        returned_at=now - datetime.timedelta(days=19),
        fine_amount=0,
    )
    on_time_borrow = BookBorrow(
        book_id=on_time_book.id,
        student_id=student.id,
        class_section_id=class_section.id,
        borrowed_at=now - datetime.timedelta(days=2),
    )
    db_session.add_all([overdue_borrow, already_returned_borrow, on_time_borrow])
    await db_session.flush()

    updated_count = await apply_overdue_fines(db_session)

    assert updated_count == 1
    assert overdue_borrow.fine_amount == 200
    assert already_returned_borrow.fine_amount == 0  # untouched
    assert on_time_borrow.fine_amount == 0


@pytest.mark.asyncio
async def test_apply_overdue_fines_never_double_charges(db_session, class_section):
    """Recomputes to the correct value rather than incrementing -- running the job
    twice for the same elapsed time must not change the fine a second time.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    student = Student(name="Idempotent Test Student", roll_number=556, class_section_id=class_section.id)
    db_session.add(student)
    await db_session.flush()

    book = Book(name="Idempotent Book", author="A", serial_number=f"FINE-{class_section.section}-4")
    db_session.add(book)
    await db_session.flush()

    borrow = BookBorrow(
        book_id=book.id,
        student_id=student.id,
        class_section_id=class_section.id,
        borrowed_at=now - datetime.timedelta(days=15),
    )
    db_session.add(borrow)
    await db_session.flush()

    first_run = await apply_overdue_fines(db_session)
    assert first_run == 1
    assert borrow.fine_amount == 200

    second_run = await apply_overdue_fines(db_session)
    assert second_run == 0  # nothing changed, so nothing counted as "updated"
    assert borrow.fine_amount == 200
