# Architecture Decision Records

Short records of the tradeoffs behind decisions that weren't obvious calls -- written
so the reasoning survives even if the code around it changes.

- [0001 — WebSockets over SSE or polling](0001-websockets-for-realtime.md)
- [0002 — Event log per domain, not a mutable status column](0002-event-log-not-status-column.md)
- [0003 — HNSW over IVFFlat for the face-embedding index](0003-hnsw-over-ivfflat.md)
- [0004 — Recompute the overdue fine, never increment it](0004-fine-recompute-not-increment.md)
- [0005 — In-memory WS broadcast is single-instance only (known limitation)](0005-ws-broadcast-single-instance-limitation.md)
