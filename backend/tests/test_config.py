import pytest

from app.config import Settings


def test_neon_urls_preserve_tls_password_and_direct_migration_connection():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:p%25ss@pooled.example/db?sslmode=require",
        database_url_unpooled="postgresql://user:p%25ss@direct.example/db?sslmode=require",
    )
    runtime = settings.sqlalchemy_url()
    migration = settings.sqlalchemy_url(migrations=True)
    assert runtime.drivername == "postgresql+psycopg"
    assert runtime.password == "p%ss"
    assert runtime.query["sslmode"] == "require"
    assert migration.host == "direct.example"
    assert "p%ss" not in repr(settings)


def test_database_rejects_sqlite():
    settings = Settings(_env_file=None, database_url="sqlite:///test.db")
    with pytest.raises(ValueError, match="PostgreSQL"):
        settings.sqlalchemy_url()
