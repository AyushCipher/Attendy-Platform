# ADR 0005: In-memory WS broadcast is single-instance only (known limitation)

## Status
Accepted for current scale. Documented rather than fixed — see rationale below.

## Context
`attendance_feed_manager` (`app/ws/connection_manager.py`) holds every connected
`/ws/attendance-feed` socket in a plain in-process `set`. `broadcast()` iterates
that set directly and calls `send_text` on each connection.

This works correctly as long as there is exactly one backend process. It breaks
the moment there is more than one:
- Backend deployed behind a load balancer with 2+ replicas.
- A rolling deploy briefly running old and new instances side by side.

In that world, a confirmed attendance/meal/borrow event broadcasts only to the
sockets held by *the replica that handled that WS request* — an admin dashboard
tab connected to a different replica never sees it, with no error raised anywhere;
it just silently doesn't update until that tab is refreshed and happens to poll
fresh data through the REST API instead.

## Options considered
- **Redis pub/sub** — each replica subscribes to a channel on connect and
  publishes on broadcast instead of iterating local sockets directly; any replica
  can then fan a message out to sockets held by any other replica. This is the
  standard fix and is a contained change (a thin adapter behind the same
  `connect`/`disconnect`/`broadcast` interface `ConnectionManager` already
  exposes), but it adds a new service to run, monitor, and reason about failure
  modes for (what happens to a broadcast if Redis is briefly unreachable?).
- **Sticky sessions at the load balancer** — pin a client to one replica. Doesn't
  actually fix cross-replica broadcast (a different client on a different replica
  still misses the event), it only hides the symptom for a single reconnecting
  client; rejected as a non-fix.
- **Do nothing, document it** — correct today: this app runs as a single backend
  instance (Docker Compose / a single Neon-backed deployment), and there is no
  multi-replica deployment in use.

## Decision
Leave `ConnectionManager` in-memory and single-instance for now; adding Redis
would be infrastructure carried for a scaling scenario this deployment doesn't
have. If a multi-replica deployment becomes real, swap `ConnectionManager`'s
internals for a Redis pub/sub-backed implementation behind the same
`connect`/`disconnect`/`broadcast` method signatures — every call site
(`app/ws/recognize.py`'s `_mark_and_broadcast`, `app/ws/feed.py`) is already
written against that interface, not against `set` internals, so the swap doesn't
touch calling code.

## Consequences
- Correct and simplest-possible today; silently incomplete the moment a second
  backend instance exists. Anyone scaling this out needs to read this ADR first,
  not discover the gap via a dashboard that stops updating.
