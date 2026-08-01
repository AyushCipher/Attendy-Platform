# Attendy — Real-Time Face Recognition Attendance System

A full-stack rewrite of a legacy Flask/OpenCV school attendance prototype into a
real-time, production-shaped application: **React + Tailwind**, **FastAPI**, and
**PostgreSQL + pgvector** for both relational data and face-embedding search.

**Project code lives in [`attendy-v2/`](attendy-v2/)** — see
[`attendy-v2/README.md`](attendy-v2/README.md) for setup instructions and
[`attendy-v2/docs/ARCHITECTURE.md`](attendy-v2/docs/ARCHITECTURE.md) for the system
design and the reasoning behind the harder decisions.

## What it does

- **Enrolls** a student's face through a browser-guided burst-capture wizard — just a
  webcam, no special hardware.
- **Recognizes** faces live over WebSocket, smoothing across frames (5-of-8 agreement)
  and gating on a motion-based liveness check before ever writing an attendance record.
- **Marks attendance instantly** in Postgres the moment a face is confirmed, and pushes
  that confirmation to every open dashboard tab in real time — no manual refresh.
- **Filters** the attendance sheet by class, section, date, and status entirely
  server-side, exports it to Excel, and surfaces attendance-rate trends and
  chronic-absentee flags on an analytics dashboard.

## Why it exists

The original prototype used OpenCV's LBPH face recognizer trained on 1-3
low-resolution photos per student — with enrollment and live recognition even using
*different* detection parameters, a real bug rather than a tuning problem. Rather than
patch it, this project replaces the recognition engine (ArcFace embeddings + pgvector
similarity search), the data layer (CSV files → normalized Postgres schema), and the
frontend (server-rendered templates → React/Tailwind), while deliberately keeping the
one part of the original design that was genuinely good: temporal smoothing across
frames before ever trusting a recognition.

## Stack

React · TypeScript · Tailwind CSS · Vite · FastAPI · SQLAlchemy (async) · PostgreSQL ·
pgvector · InsightFace (ArcFace) · WebSockets · Docker · GitHub Actions

## Quickstart

```bash
cd attendy-v2
docker compose --profile full up --build
```

Full setup, testing, and deployment instructions: [`attendy-v2/README.md`](attendy-v2/README.md).
