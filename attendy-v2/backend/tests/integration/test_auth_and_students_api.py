import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.base import async_session_factory, get_db
from app.db.models.admin import Admin
from app.main import app


@pytest.fixture
async def api_client(db_session):
    # The app's own `get_db` would open a fresh connection per request, which can't
    # see rows this test's `db_session` has only flushed. Overriding it to reuse the
    # same session lets a real HTTP request (login, create-student, ...) observe
    # fixture-created rows and each other's writes within one test.
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def test_admin(db_session):
    # Routes under test (login) call db.commit(), which is real and outlives this
    # fixture's session -- a unique email + explicit teardown keeps repeated local
    # runs from hitting the admins_email_key unique constraint.
    email = f"pytest-admin-{uuid.uuid4().hex[:8]}@attendy.dev"
    admin = Admin(email=email, password_hash=hash_password("pytest-password"), full_name="Pytest Admin")
    db_session.add(admin)
    await db_session.flush()
    admin_id = admin.id

    yield admin

    async with async_session_factory() as cleanup_session:
        existing = await cleanup_session.get(Admin, admin_id)
        if existing is not None:
            await cleanup_session.delete(existing)
            await cleanup_session.commit()


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(api_client, test_admin):
    response = await api_client.post(
        "/api/auth/login", json={"email": test_admin.email, "password": "pytest-password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["admin"]["email"] == test_admin.email
    assert "access_token" in body


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(api_client, test_admin):
    response = await api_client.post(
        "/api/auth/login", json={"email": test_admin.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(api_client):
    response = await api_client.post(
        "/api/auth/login", json={"email": "nobody@nowhere.dev", "password": "whatever"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_students_endpoint_requires_auth(api_client):
    response = await api_client.get("/api/students")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_and_filter_students(api_client, test_admin):
    login = await api_client.post(
        "/api/auth/login", json={"email": test_admin.email, "password": "pytest-password"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Routes under test commit for real (see api_client's fixture docstring), so a
    # random roll number avoids colliding with a previous local run's leftover row
    # under the same fixed grade/section.
    roll_number = uuid.uuid4().int % 90000 + 10000

    # grade/section (not class_section_id) is the actual create payload now -- the
    # route get-or-creates the class_section row, matching the two-dropdown picker
    # in the frontend (Class 1-12 / Section A-F) that replaced the old free-text
    # "+ New class/section" flow.
    create_resp = await api_client.post(
        "/api/students",
        json={"name": "Filter Test Student", "roll_number": roll_number, "grade": 9, "section": "A"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["face_enrolled"] is False
    class_section_id = created["class_section"]["id"]

    try:
        # Filtering by this class_section should surface exactly the student we just made.
        list_resp = await api_client.get(
            "/api/students", params={"class_section_id": class_section_id}, headers=headers
        )
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert any(s["id"] == created["id"] for s in body["items"])

        # A different class_section filter must exclude it.
        other_resp = await api_client.get(
            "/api/students",
            params={"class_section_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )
        assert other_resp.status_code == 200
        assert not any(s["id"] == created["id"] for s in other_resp.json()["items"])

        # Duplicate roll number in the same class/section must be rejected.
        dup_resp = await api_client.post(
            "/api/students",
            json={"name": "Duplicate Roll", "roll_number": roll_number, "grade": 9, "section": "A"},
            headers=headers,
        )
        assert dup_resp.status_code == 409

        # An invalid section is rejected before it ever reaches the database.
        invalid_resp = await api_client.post(
            "/api/students",
            json={"name": "Bad Section", "roll_number": roll_number + 1, "grade": 9, "section": "Z"},
            headers=headers,
        )
        assert invalid_resp.status_code == 422
    finally:
        async with async_session_factory() as cleanup_session:
            from app.db.models.student import Student

            existing = await cleanup_session.get(Student, created["id"])
            if existing is not None:
                await cleanup_session.delete(existing)
                await cleanup_session.commit()
