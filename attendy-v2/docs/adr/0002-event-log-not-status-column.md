# ADR 0002: Event log per domain, not a mutable status column

## Status
Accepted

## Context
Three domains need a "has X happened for Y today/right now" answer: attendance
(present today?), meals (ate today?), and library (book currently out?). The
legacy Flask app modeled this as CSV rows written on the scan event, which worked
by accident rather than design.

Two shapes were available for the rewrite:
- **Mutable status column** — e.g. `students.attendance_status`, flipped by the
  scan handler, reset by a midnight job. Cheap to query ("is present" is a column
  read) but creates a second source of truth: the column can drift from what
  actually happened if the reset job fails, runs twice, or a manual DB edit skips
  it — and there is no history, only the current value.
- **Event log (append-only rows)** — `attendance_records` / `meal_records` /
  `book_borrows`, one row per confirmed event. "Present today" is `EXISTS(...
  WHERE event_date = today)`; absence is the *absence* of a row, never a written
  "absent" value.

## Decision
Event log for all three domains. `books` itself has no `is_borrowed` column
(`app/db/models/book.py`) — "currently borrowed" is always
`EXISTS(book_borrows WHERE book_id = X AND returned_at IS NULL)`, computed at read
time in `books.py`'s `list_books`/`_to_book_out`.

## Consequences
- Nothing to reset at midnight, and no job can leave the data in a half-migrated
  state — a new day just means new `event_date` values, not a column flip.
- Analytics (chronic-absentee list, attendance-rate trend) are plain aggregate
  queries over history that already exists, not a separate audit log bolted on
  after the fact.
- The tradeoff is that "is present" is a query, not a column read — irrelevant at
  this app's scale (one query per admin dashboard load, not a hot path), but would
  need an index/materialized view if this were serving thousands of concurrent
  status checks.
- This is also what makes the book-borrow concurrency fix
  ([partial unique index](../../backend/alembic/versions/d4471cc5a486_add_partial_unique_index_for_one_open_.py))
  possible in the first place: "one open borrow per book" is expressible as a DB
  constraint only because openness is derived from rows, not from an
  app-toggled flag a constraint can't see.
