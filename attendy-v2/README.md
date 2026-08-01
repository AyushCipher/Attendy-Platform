# Attendy — Real-Time Face Recognition Attendance System

A full rewrite of a legacy Flask/OpenCV attendance system, built to fix a real bug
(face recognition that didn't work reliably) and turn a CSV-file prototype into a
properly modeled, real-time, portfolio-grade application.

**Stack:** React + Tailwind (Vite) · FastAPI · PostgreSQL + pgvector · InsightFace (ArcFace)
· WebSockets · Docker

## What it does

- Enrolls a student's face via a browser-guided burst-capture wizard (no special
  hardware, just a webcam).
- Recognizes faces live over WebSocket, with temporal smoothing (5-of-8 frame
  agreement) and a bounding-box-motion liveness check before ever writing an attendance
  record.
- Marks attendance in Postgres the instant a face is confirmed, and pushes that
  confirmation to every open dashboard tab in real time -- no manual refresh.
- Filters the attendance sheet by class, section, date, and status entirely
  server-side (the legacy app's class/section filter dropdown was dead code that never
  actually filtered anything).
- Exports the filtered sheet to Excel, and surfaces attendance-rate trends and
  chronic-absentee flags on an analytics dashboard.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the system diagram and the
reasoning behind the harder design decisions (why browser-side camera capture, why an
event-log attendance model, why WebSockets over SSE).

## Why this exists

The original project (kept at [`../Attendy-main`](../Attendy-main) as a before/after
reference) used OpenCV's LBPH face recognizer trained on 1-3 low-resolution photos per
student, with enrollment and live recognition using *different* detection parameters --
a bug, not a tuning problem. Rather than patch LBPH, this rewrite replaces the
recognition engine (ArcFace embeddings + pgvector similarity search), the data layer
(CSV files → normalized Postgres schema), and the frontend (server-rendered Flask
templates → React/Tailwind), while deliberately keeping the one part of the legacy
design that was genuinely good: temporal smoothing across frames before ever trusting a
recognition.

## Running it locally

**Fastest path (fully containerized):**

```bash
docker compose --profile full up --build

# in a second terminal, once the backend container is healthy:
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_admin --email admin@attendy.dev --name "Admin" --password admin123
```

Then open `http://localhost:8080`. First run will download the ~300MB InsightFace
`buffalo_l` model pack on first use.

**Day-to-day dev (faster iteration, native processes):**

```bash
# 1. Database only
docker compose up -d db

# 2. Backend
cd backend
python -m venv venv && source venv/Scripts/activate  # or venv/bin/activate on macOS/Linux
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

## Testing

```bash
# Backend (spins up an isolated attendy_test database automatically)
cd backend && pytest -v

# Frontend
cd frontend && npm run test
```

## Deploying to Neon or Supabase instead of local Postgres

See [`docs/NEON_SUPABASE_SWAP.md`](docs/NEON_SUPABASE_SWAP.md) -- it's a `DATABASE_URL`
change, not a code change.

## Scope notes (what this deliberately does not include)

- **Liveness** is a bounding-box-motion heuristic, not a production anti-spoofing
  model -- enough to block a photo held up to the camera, not a security control.
- **Auth** is a single access/refresh JWT pair with no rotation or session
  revocation list -- appropriate for a single-admin deployment, not multi-tenant SaaS.
- **Library and mid-day-meal tracking** (present in the legacy app) are intentionally
  not ported yet; this rewrite focused on making the attendance module solid first.
