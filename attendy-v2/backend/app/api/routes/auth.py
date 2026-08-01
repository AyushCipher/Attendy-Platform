from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_admin,
    verify_password,
)
from app.db.base import get_db
from app.db.models.admin import Admin
from app.schemas.auth import AdminOut, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).where(Admin.email == payload.email))
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    admin.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(admin.id)
    refresh_token = create_refresh_token(admin.id)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token, admin=AdminOut.model_validate(admin))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
):
    if refresh_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")

    admin_id = decode_token(refresh_token, expected_type="refresh")
    admin = await db.get(Admin, admin_id)
    if admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin not found")

    access_token = create_access_token(admin.id)
    new_refresh_token = create_refresh_token(admin.id)
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=access_token, admin=AdminOut.model_validate(admin))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")
    return {"status": "ok"}


@router.get("/me", response_model=AdminOut)
async def me(admin: Admin = Depends(get_current_admin)):
    return AdminOut.model_validate(admin)
