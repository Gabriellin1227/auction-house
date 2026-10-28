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
def client(database, monkeypatch, request, tmp_path):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.db.session import get_session
    from app.main import app

    monkeypatch.setenv("AUTH_SECRET", "test-only-signing-key-" + "x" * 40)
    monkeypatch.setenv("AUDIT_DIR", str(tmp_path / "audit"))
    monkeypatch.setenv("AUDIT_SECRET", "test-only-audit-key-" + "y" * 40)
    monkeypatch.setenv("EVENTS_ENABLED", str(getattr(request, "param", False)).lower())
    monkeypatch.setattr("app.events.runtime.get_engine", lambda: database)
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


@pytest.fixture
def market(client, database):
    from datetime import timedelta

    from sqlalchemy import func, select

    from app.auth.security import create_token
    from app.bids.signing import ZERO_HASH, head_record, sign
    from app.db.models import AuditHead, Lot, User, Wallet

    with Session(database) as session, session.begin():
        users = [
            User(
                id=uuid4(),
                name=f"Pessoa {i}",
                email=f"pessoa{i}@example.com",
                password_hash="unused-in-this-fixture",
                role="auctioneer" if i == 0 else "bidder",
            )
            for i in range(3)
        ]
        session.add_all(users)
        session.flush()
        session.add_all(
            [Wallet(user_id=user.id, balance_cents=10000) for user in users]
        )
        now = session.scalar(select(func.clock_timestamp()))
        lots = [
            Lot(
                id=uuid4(),
                seller_id=users[0].id,
                source_provider="test",
                external_item_id=str(i),
                source_url="https://example.com/item",
                item_title="Obra de teste",
                item_attributes={"category": "fine-art"},
                local_image_key="test.jpg",
                opening_bid_cents=8000,
                min_increment_cents=1000,
                starts_at=now - timedelta(hours=1),
                original_ends_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
            )
            for i in range(2)
        ]
        session.add_all(lots)
        session.flush()
        session.add_all(
            [
                AuditHead(
                    lot_id=lot.id,
                    last_sequence=0,
                    last_hash=ZERO_HASH,
                    key_version=1,
                    signature=sign(head_record(lot.id, 0, ZERO_HASH)),
                )
                for lot in lots
            ]
        )
        ids = [u.id for u in users]
        lot_ids = [lot.id for lot in lots]
    return {
        "users": ids,
        "lots": lot_ids,
        "headers": [{"Authorization": "Bearer " + create_token(uid)} for uid in ids],
    }
