import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _test_database_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit(parts._replace(path="/attendy_test"))


_dev_db_url_for_bootstrap = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://attendy:attendy_dev@localhost:5455/attendy"
)
# Set BEFORE any `app.*` import so `get_settings()` (env-driven, lru_cache'd) resolves
# to the isolated test database everywhere in the app, not the dev DB with real demo data.
os.environ["DATABASE_URL"] = _test_database_url(_dev_db_url_for_bootstrap)

import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.db.base import Base, async_session_factory, engine  # noqa: E402
from app.db.models import *  # noqa: E402, F401, F403


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _test_database():
    """Creates (once) and schema-initializes a dedicated `attendy_test` database on
    the same Postgres server, so the test suite never touches manually-created dev/
    demo data (this bug was found the hard way: tests silently depended on the dev
    DB's face_embeddings table being empty, which broke the moment real students got
    enrolled through manual API testing in the same session).

    Base.metadata.create_all only creates *missing* tables -- it does NOT add new
    columns/constraints/indexes to a table that already exists from a previous run.
    A schema change to an existing model (e.g. adding an index) needs a locally
    already-created `attendy_test` DB dropped by hand once (`DROP DATABASE
    attendy_test` against the dev server) so it gets rebuilt from the current models.
    CI doesn't hit this since its Postgres service starts empty every run.
    """
    admin_engine = create_async_engine(_dev_db_url_for_bootstrap, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = 'attendy_test'")
        )
        if not exists:
            await conn.execute(text("CREATE DATABASE attendy_test"))
    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield


@pytest_asyncio.fixture
async def db_session():
    """One session per test. NOTE: routes under test call `db.commit()` themselves
    (e.g. login, student creation) -- when a test drives the app through real HTTP
    requests (see api_client's dependency_override), those commits are real within
    the isolated test database. Fixtures that create data use randomized identifiers
    and explicit teardown (see `class_section` below) rather than relying on
    transaction rollback for isolation.
    """
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def class_section(db_session):
    from app.db.models.class_section import ClassSection

    unique_section = f"T{uuid.uuid4().hex[:3].upper()}"  # section is VARCHAR(4)
    cs = ClassSection(grade=9, section=unique_section)
    db_session.add(cs)
    await db_session.flush()
    cs_id = cs.id

    yield cs

    async with async_session_factory() as cleanup_session:
        # Students created against this class_section via a real API call (committed
        # by the route, not this fixture) must go first -- no ON DELETE CASCADE on
        # students.class_section_id.
        await cleanup_session.execute(
            text("DELETE FROM students WHERE class_section_id = :id"), {"id": cs_id}
        )
        await cleanup_session.execute(text("DELETE FROM class_sections WHERE id = :id"), {"id": cs_id})
        await cleanup_session.commit()
