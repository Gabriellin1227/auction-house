import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND = Path(__file__).resolve().parents[1]


def migrate(engine, revision="head", *, downgrade=False):
    config = Config(str(BACKEND / "alembic.ini"))
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        operation = command.downgrade if downgrade else command.upgrade
        operation(config, revision)


@pytest.fixture
def empty_database():
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    url = make_url(raw_url).set(drivername="postgresql+psycopg")
    schema = "test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def database(empty_database):
    migrate(empty_database)
    return empty_database


@pytest.fixture
def session(database):
    with Session(database) as session:
        yield session


@pytest.fixture
def client(database, monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.db.session import get_session
    from app.main import app

    monkeypatch.setenv("AUTH_SECRET", "test-only-signing-key-" + "x" * 40)
    monkeypatch.setenv("AUDIT_SECRET", "test-only-audit-key-" + "y" * 40)
    get_settings.cache_clear()

    def test_session():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        get_settings.cache_clear()
