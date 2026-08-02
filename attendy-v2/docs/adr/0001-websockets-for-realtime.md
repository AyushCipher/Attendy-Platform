# ADR 0001: WebSockets over SSE or polling for scanning and the live feed

## Status
Accepted

## Context
Two real-time paths exist: `/ws/recognize` streams camera frames to the server and
gets back per-frame overlay data (bounding boxes, confirm/reject status), and
`/ws/attendance-feed` pushes confirmed events out to every open admin dashboard tab.
The transport had to support **client-to-server streaming** for the first path (a
JPEG frame roughly every 200ms) and **server-to-many-clients push** for the second.

Alternatives considered:
- **HTTP polling** — the client would need to re-POST each frame and poll the feed
  endpoint on an interval. Doubles connection overhead (new TCP/TLS handshake
  cost is avoided by keep-alive, but HTTP request framing still applies per frame)
  and adds a polling-interval floor to feed latency for no benefit.
- **Server-Sent Events (SSE)** — a good fit for the one-way `/attendance-feed`
  broadcast, but SSE is server-to-client only. `/ws/recognize` needs the client to
  keep sending frames, so it would still need a second channel (regular POSTs) for
  the upload direction, splitting one logical exchange into two connections with
  separate lifecycles to keep in sync.
- **WebSockets** — one bidirectional connection per role. `/ws/recognize` sends
  frames upstream and receives overlay JSON downstream on the same socket;
  `/ws/attendance-feed` only needs the downstream half but reuses the same
  transport and connection-manager pattern.

## Decision
Use native FastAPI/Starlette WebSockets for both channels, with a single
`ConnectionManager` per channel handling accept/broadcast/disconnect.

## Consequences
- One connection per scan session instead of a request per frame — lower overhead
  at the ~5fps this app actually sends.
- `/ws/attendance-feed`'s `ConnectionManager` (`app/ws/connection_manager.py`) is
  in-memory and per-process, which caps this design to a single backend instance —
  see [ADR 0005](0005-ws-broadcast-single-instance-limitation.md).
- No automatic reconnect/backoff is provided by the browser WebSocket API the way
  `EventSource` (SSE) gives you for free; the frontend's `useRecognitionSocket` hook
  has to handle its own connect/cleanup lifecycle instead.
