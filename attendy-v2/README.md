# Attendy — Real-Time Face Recognition Attendance System

A full rewrite of a legacy Flask/OpenCV attendance system, built to fix a real bug
(face recognition that didn't work reliably) and turn a CSV-file prototype into a
properly modeled, real-time, portfolio-grade application.

**Stack:** React · TypeScript · Tailwind CSS (Vite) · FastAPI · SQLAlchemy (async) ·
PostgreSQL + pgvector · InsightFace (ArcFace) · WebSockets · Docker · GitHub Actions

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Why This Exists](#why-this-exists)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Deploying to Neon or Supabase](#deploying-to-neon-or-supabase)
- [Scope & Known Limitations](#scope--known-limitations)
- [Roadmap](#roadmap)

---

## Overview

Attendy is a school management system that recognizes students from a live webcam
feed and marks attendance, meals, and library activity the instant they're confirmed
— with confirmations pushed to every open admin dashboard in real time. It replaces
a legacy Flask + OpenCV prototype that used CSV files for storage and a face
recognizer that simply didn't work reliably after training.

## Features

- **Guided face enrollment** — a browser-based burst-capture wizard walks a student
  through several poses (straight, left, right, chin down), extracting a 512-d ArcFace
  embedding per usable capture. No special hardware, just a webcam. The first usable
  capture also becomes the student's profile photo.
- **QR ID cards** — every student and every registered book gets a QR code encoding
  its own UUID (not `"{name} {roll}"` or `"BOOK:<id>:<name>"` like the legacy app,
  which silently broke on multi-word names) — downloadable for printing.
- **Three scan modes, one shared pipeline** (`/ws/recognize?mode=`), not three
  parallel implementations:
  - **Attendance** — face *or* QR marks the daily attendance sheet.
  - **Mess** — face recognition only, no QR fallback, marks the daily meal sheet.
  - **Library** — a two-step scan (identify the student by face or QR, then scan a
    book's QR) that borrows or returns it, rejecting a book already out to someone
    else.
- **Temporal smoothing + liveness** — a per-connection face tracker (IoU-based) requires
  5-of-8 consistent frame matches before confirming an identity, plus a
  bounding-box-motion check so a photo held up to the camera can't be marked present.
  (QR identification skips this gate entirely — a decoded UUID is an exact match,
  nothing probabilistic to smooth over.)
- **Overdue library fines** — ₹100 per 7-day period a book remains unreturned,
  recomputed (not incremented) daily by a scheduled job, so it can never
  double-charge; cleared only by an explicit admin "settle fine" action, independent
  of the book actually being returned.
- **Instant, server-side-filtered attendance/meal sheets** — filter by class, section,
  date, and status, all resolved in SQL — not the dead client-side filter dropdown the
  legacy admin UI shipped with.
- **Live dashboard updates** — confirmed attendance is broadcast over a second
  WebSocket channel and patched directly into the frontend's query cache, so every
  open tab updates without a manual refresh or polling.
- **Analytics** — attendance-rate trend chart and a chronic-absentee list (configurable
  absence-rate threshold), computed over school days only (weekends excluded).
- **Excel export** of the currently filtered attendance sheet.
- **Class/section management**, soft-deletable students, and JWT-based admin auth
  (access + httpOnly refresh token).

## Why This Exists

The original project used OpenCV's **LBPH** face recognizer trained on 1-3
low-resolution photos per student — and enrollment used *different* Haar-cascade
detection parameters than live recognition. That's a bug, not a tuning problem: LBPH
had no chance of generalizing from a handful of static training photos to live webcam
conditions (pose, lighting, distance).

Rather than patch LBPH, this project replaces:

- the **recognition engine** — ArcFace embeddings (InsightFace) + pgvector similarity
  search, with enrollment and live recognition sharing the exact same
  capture/detection code path by construction, so the two can't drift apart again;
- the **data layer** — CSV files → a normalized Postgres schema with a proper
  `attendance_records` event log (absence is the *absence* of a row, never written);
- the **frontend** — server-rendered Flask templates → React + Tailwind.

One part of the legacy design was genuinely good and is deliberately kept: temporal
smoothing across multiple frames before ever trusting a single recognition result.

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        Cam[Camera getUserMedia]
        Scan[Scan page]
        Dash[Attendance / Dashboard]
    end

    subgraph Backend [FastAPI]
        WSRecognize[/ws/recognize/]
        WSFeed[/ws/attendance-feed/]
        API[REST API]
        Engine[Face engine\nInsightFace / ArcFace]
        Tracker[Temporal smoothing\n+ liveness]
    end

    DB[(Postgres + pgvector)]

    Cam --> Scan -- JPEG frames --> WSRecognize
    WSRecognize --> Engine --> Tracker
    WSRecognize <-- cosine search --> DB
    WSRecognize -- insert attendance row --> DB
    WSRecognize -- overlay JSON --> Scan
    WSRecognize -- broadcast --> WSFeed --> Dash
    Dash -- filtered query --> API --> DB
```

Full system design, the event-log data model, and the reasoning behind harder
decisions (browser-side camera capture, WebSockets over SSE, why an event log instead
of a status column) live in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Tailwind CSS v4, Vite, TanStack Query, Zustand, React Hook Form + Zod, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, PyJWT, bcrypt, Alembic |
| Face recognition | InsightFace (`buffalo_l` / ArcFace), ONNX Runtime, OpenCV (headless) |
| QR codes | `qrcode` (generation), OpenCV `QRCodeDetector` (decoding) |
| Scheduling | APScheduler (daily overdue-fine job) |
| Database | PostgreSQL 16 + [`pgvector`](https://github.com/pgvector/pgvector) (HNSW cosine index) |
| Real-time | Native FastAPI/Starlette WebSockets |
| Testing | pytest + pytest-asyncio (isolated test database), Vitest + React Testing Library |
| Infra | Docker, Docker Compose, nginx (frontend reverse proxy), GitHub Actions CI |

## Project Structure

```
attendy-v2/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # REST endpoints: auth, students, class_sections,
│   │   │                     #   attendance (+ /meals), books (+ /borrows)
│   │   ├── core/             # settings (pydantic-settings) and JWT/password security
│   │   ├── db/
│   │   │   └── models/       # SQLAlchemy models: admin, student, class_section,
│   │   │                     #   face_embedding (pgvector), attendance, meal,
│   │   │                     #   book, book_borrow
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # face_engine, matcher (pgvector search), tracker
│   │   │                     #   (temporal smoothing + liveness), attendance_service,
│   │   │                     #   meal_service, library_service (borrow/fine formula),
│   │   │                     #   fine_job (scheduled), qr_service, photo_service,
│   │   │                     #   analytics_service, export_service (xlsx)
│   │   ├── ws/                # /ws/recognize (mode=attendance|mess|library)
│   │   │                     #   and /ws/attendance-feed handlers
│   │   └── main.py            # incl. APScheduler lifespan for the fine job
│   ├── alembic/               # DB migrations (incl. `CREATE EXTENSION vector`)
│   ├── scripts/               # seed_admin, calibrate_threshold, WS smoke test
│   ├── tests/                 # pytest: unit/ + integration/ (own isolated DB)
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── routes/
│       │   ├── login/
│       │   └── admin/
│       │       ├── dashboard/    # trend chart + chronic-absentee list
│       │       ├── attendance/   # filterable, live-updating sheet + export
│       │       ├── meals/        # meal sheet (mirrors attendance)
│       │       ├── library/      # book registry + currently-borrowed/fines table
│       │       ├── students/     # CRUD + face enrollment wizard + ID card + photo
│       │       └── scan/         # mode picker + attendance/mess/library scan pages
│       ├── components/{layout,common}/
│       ├── hooks/                 # React Query hooks incl. the WS feed cache-patcher
│       │                          #   and the shared useRecognitionSocket
│       ├── lib/                   # axios client (auto refresh), query client, canvas overlay
│       └── store/                 # Zustand auth store
├── docs/
│   ├── ARCHITECTURE.md
│   └── NEON_SUPABASE_SWAP.md
├── docker-compose.yml          # db + adminer always; backend + frontend under `full` profile
└── .github/workflows/ci.yml
```

## API Reference

All routes except `/api/auth/login`, `/api/auth/refresh`, and `/api/health` require a
bearer token.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Authenticate, returns access token + sets refresh cookie |
| POST | `/api/auth/refresh` | Exchange refresh cookie for a new access token |
| POST | `/api/auth/logout` | Clear the refresh cookie |
| GET | `/api/auth/me` | Current admin profile |
| GET / POST | `/api/class-sections` | List / create class-sections |
| DELETE | `/api/class-sections/{id}` | Delete a class-section |
| GET / POST | `/api/students` | List (filterable by grade/section/status/search) / create students |
| GET / PATCH / DELETE | `/api/students/{id}` | Read / update / soft-delete a student |
| POST | `/api/students/{id}/enroll-face` | Upload burst-capture photos → store embeddings + profile photo |
| DELETE | `/api/students/{id}/face-embeddings` | Clear stored embeddings (re-enroll) |
| GET | `/api/students/{id}/qr-code` | Student ID-card QR (PNG, encodes the student UUID) |
| GET | `/api/students/{id}/photo` | Student's profile photo (PNG/JPEG, captured at enrollment) |
| GET | `/api/attendance` | Filterable attendance sheet (date, class, status, search) |
| POST | `/api/attendance/manual` | Admin override (mark present/absent for a date) |
| GET | `/api/attendance/export` | Export the filtered sheet as `.xlsx` |
| GET | `/api/attendance/meals` | Filterable meal sheet — same shape as `/attendance` |
| GET | `/api/attendance/analytics/summary` | Daily present/absent counts over a date range |
| GET | `/api/attendance/analytics/chronic-absentees` | Students over an absence-rate threshold |
| GET / POST | `/api/books` | List (filterable) / register books |
| DELETE | `/api/books/{id}` | Soft-delete (retire) a book |
| GET | `/api/books/{id}/qr-code` | Book QR (PNG, encodes the book UUID) |
| GET | `/api/books/borrows` | Currently-borrowed books with live-computed fines |
| POST | `/api/books/borrows/{id}/settle-fine` | Mark a fine as settled (does not touch the borrow itself) |
| WS | `/ws/recognize?mode=attendance\|mess\|library` | Bidirectional: JPEG frames in, recognition/scan overlay + marks out |
| WS | `/ws/attendance-feed` | Broadcast channel: live `attendance_confirmed` / `meal_confirmed` events |
| GET | `/api/health` | Health check |

## Getting Started

### Fastest path — fully containerized

```bash
cd attendy-v2
docker compose --profile full up --build

# in a second terminal, once the backend container is healthy:
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_admin --email admin@attendy.dev --name "Admin" --password admin123
```

Open `http://localhost:8080`. First run downloads the ~300MB InsightFace `buffalo_l`
model pack.

### Day-to-day development (native processes, faster iteration)

```bash
# 1. Database only
docker compose up -d db

# 2. Backend
cd backend
python -m venv venv && source venv/Scripts/activate   # venv/bin/activate on macOS/Linux
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_admin --email admin@attendy.dev --name "Admin" --password admin123
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
npm install
npm run dev
```

Open the printed Vite dev URL (default `http://localhost:5173`).

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and adjust as needed — every value has a
working local-dev default baked into `app/core/config.py`, so a fresh clone runs
without a `.env` at all:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local Docker Postgres | SQLAlchemy async connection string |
| `JWT_SECRET` | dev placeholder | **Change this in any real deployment** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed frontend origins |
| `FACE_MATCH_THRESHOLD` | `0.38` | Cosine-similarity cutoff for a face match |
| `FACE_MODEL_PACK` | `buffalo_l` | InsightFace model pack |

## Testing

```bash
# Backend — spins up an isolated `attendy_test` database automatically, so it never
# touches your dev data
cd backend && pytest -v

# Frontend
cd frontend && npm run test
```

CI (`.github/workflows/ci.yml`) runs both suites plus lint (`ruff`, `oxlint`) and both
production builds on every push/PR to `main`.

## Deploying to Neon or Supabase

Both are wire-compatible Postgres and support `pgvector`, so switching from the local
Docker database is a `DATABASE_URL` change, not a code change — see
[`docs/NEON_SUPABASE_SWAP.md`](docs/NEON_SUPABASE_SWAP.md).

## Scope & Known Limitations

- **Liveness** is a bounding-box-motion heuristic, not a production anti-spoofing
  model — enough to block a photo held up to the camera, not a security control.
- **Auth** is a single access/refresh JWT pair with no rotation or session-revocation
  list — appropriate for a single-admin deployment, not multi-tenant SaaS.
- **Single-instance real-time**: the WebSocket broadcast manager is in-process
  (appropriate at this scale); a multi-instance deployment would swap it for Redis
  pub/sub without changing calling code.
- **CPU-only inference** is adequate for a single-camera admin/kiosk setup, not sized
  for many concurrent camera streams.

## Roadmap

- PDF export alongside the existing Excel export.
- Email/SMS absence notifications to parents.
- Email/SMS reminders for students with an unsettled library fine.
