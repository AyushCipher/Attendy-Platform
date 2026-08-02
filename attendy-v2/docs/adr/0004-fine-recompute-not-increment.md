# ADR 0004: Recompute the overdue fine, never increment it

## Status
Accepted

## Context
`fine_job.apply_overdue_fines` runs daily and needs to raise `fine_amount` on any
book still out past its grace period. Two ways to update that number:

- **Increment** — `fine_amount += 100` whenever the job finds a borrow past a new
  7-day boundary. Simple, but not idempotent: if the job fires twice in a day
  (APScheduler misfire, manual re-run, a redeploy that restarts the scheduler), the
  student gets double-charged for the same overdue period. It also requires the
  job to track *which* periods it already charged, which is more state than the
  problem needs.
- **Recompute** — `expected = (days_late // 7) * 100`
  (`library_service.compute_fine`); set `fine_amount = expected` if higher than
  the current value. The function of elapsed time alone, not of how many times
  the job has run.

## Decision
Recompute. `compute_fine` is a pure function of `(borrowed_at, now)` shared by both
the scheduled job and the live library-scan return path
(`_handle_library_frame` in `app/ws/recognize.py`), so both are guaranteed to land
on the same number for the same borrow — there's exactly one formula, not two that
could drift.

## Consequences
- The job is safe to re-run any number of times a day, or after a gap (a missed
  day doesn't need catch-up logic — the next run just computes the correct total
  directly from elapsed time).
- `fine_amount` only ever increases via this path; it's explicitly never reset by
  a return (`open_borrow.fine_amount = compute_fine(...)` on return locks it at
  its final value) — clearing it is only ever `settle-fine`, a distinct admin
  action, per the product decision that returning a book and forgiving its fine
  are two separate facts.
- The tradeoff is that this can't express "$100 for week 1, waived, but $100 still
  due for week 2" — a partial waiver isn't representable, only settle-all-or-owe.
  That's an acceptable simplification for this app's scope; a partial-waiver
  feature would need per-period fine rows instead of one running total.
