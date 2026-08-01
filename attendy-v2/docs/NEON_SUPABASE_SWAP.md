# Switching from local Postgres to Neon or Supabase

The app was built against a local `pgvector/pgvector:pg16` Docker container so
development didn't have to wait on cloud account creation. Both Neon and Supabase are
wire-compatible standard Postgres and support the `vector` extension, so moving to
either is a **connection-string change, not a code change**.

## Steps

1. **Create the project.**
   - Neon: create a project at neon.tech, copy the connection string from the dashboard.
   - Supabase: create a project at supabase.com, copy the connection string from
     Project Settings → Database (use the "connection pooling" string for the app,
     not the direct one, if you expect more than a handful of concurrent connections).

2. **Enable `pgvector`.** Both platforms support it, but check it's actually turned on:
   - Neon: enabled by default on recent projects; if not, run `CREATE EXTENSION IF NOT
     EXISTS vector;` in the SQL editor.
   - Supabase: Database → Extensions → search "vector" → enable. (On some plans this
     needs the `postgres` role, not the default `service_role`/app role -- a one-time
     dashboard toggle, not something the app's migrations can do for you if disabled at
     the database level.)

3. **Point the app at it.** Set `DATABASE_URL` (backend/.env or your deploy platform's
   env vars) to the new connection string, using the `+asyncpg` driver prefix:

   ```
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<dbname>
   ```

4. **Run migrations against it.**

   ```bash
   cd backend
   alembic upgrade head
   ```

   This is the same migration that runs locally -- it issues `CREATE EXTENSION IF NOT
   EXISTS vector` itself as its first step, so there's no manual schema setup beyond
   what's in step 2.

5. **(Optional) Seed an admin.**

   ```bash
   python scripts/seed_admin.py
   ```

That's the entire swap. Nothing in `app/` references Neon or Supabase specifically --
they're both just Postgres from SQLAlchemy/asyncpg's point of view.
