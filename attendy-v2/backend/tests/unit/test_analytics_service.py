"""Regression test for a real bug found during manual testing: a weekend attendance
row (e.g. from a manual backfill) was being counted as a 'present day' even though
the school_days denominator only counts weekdays, silently inflating attendance and
understating absences for anyone with a weekend row in range.
"""
import datetime

import pytest

from app.db.models.attendance import AttendanceRecord
from app.services.analytics_service import get_chronic_absentees


@pytest.mark.asyncio
async def test_weekend_attendance_row_excluded_from_presence_count(db_session, class_section):
    from app.db.models.student import Student

    student = Student(name="Weekend Edge Case", roll_number=999, class_section_id=class_section.id)
    db_session.add(student)
    await db_session.flush()

    # 2026-08-01 is a Saturday.
    saturday = datetime.date(2026, 8, 1)
    monday_to_friday_start = datetime.date(2026, 7, 27)  # Monday

    db_session.add(
        AttendanceRecord(
            student_id=student.id,
            class_section_id=class_section.id,
            event_date=saturday,
            source="manual",
        )
    )
    await db_session.flush()

    results = await get_chronic_absentees(
        db_session,
        date_from=monday_to_friday_start,
        date_to=saturday,
        threshold=0.0,
        class_section_id=class_section.id,
    )

    row = next(r for r in results if r["student"].id == student.id)
    assert row["school_days"] == 5  # Mon-Fri only, Saturday excluded
    assert row["absent_days"] == 5  # the Saturday attendance row must not count as present
    assert row["absence_rate"] == 1.0
