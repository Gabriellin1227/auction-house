from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT.parent / ".env", BACKEND_ROOT / ".env"),
        extra="ignore",
    )
    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://auction:auction_dev@localhost:5433/auction_house"
    )
    database_url_unpooled: SecretStr | None = None
    cors_origins: list[str] = []
    worker_required: bool = False
    events_enabled: bool = True
    audit_dir: Path = BACKEND_ROOT / "audit"
    media_dir: Path = BACKEND_ROOT / "media"
    auth_secret: SecretStr | None = None
    audit_secret: SecretStr | None = None
    access_token_minutes: int = Field(default=30, ge=1, le=120)

    @field_validator("auth_secret", "audit_secret", mode="before")
    @classmethod
    def validate_auth_secret(cls, value):
        if value is None or value == "":
            return None
        secret = value.get_secret_value() if isinstance(value, SecretStr) else value
        if len(secret) < 32:
            raise ValueError("Segredos precisam ter ao menos 32 caracteres")
        return value

    def sqlalchemy_url(self, *, migrations: bool = False) -> URL:
        secret = self.database_url_unpooled if migrations else None
        url = make_url((secret or self.database_url).get_secret_value())
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError("Only PostgreSQL with psycopg is supported")
        return url.set(drivername="postgresql+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()
