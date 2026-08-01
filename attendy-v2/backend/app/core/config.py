from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://attendy:attendy_dev@localhost:5455/attendy"

    jwt_secret: str = "dev-secret-change-me-in-production-32bytes+"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:5173"]

    face_match_threshold: float = 0.38
    face_model_pack: str = "buffalo_l"

    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
