from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.config import get_settings
from app.db.models import AuditHead, Lot, User, Wallet
from app.seed import seed_open_lot, seed_users


@pytest.fixture
def demo(client, database, monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    get_settings.cache_clear()
    calls = []

    def item(self, item_id):
        calls.append(item_id)
        return {"id": item_id, "url": "https://example.com/art", "title": "Obra demo"}

    def image(self, item):
        root = get_settings().media_dir
        root.mkdir(parents=True, exist_ok=True)
        (root / "demo.jpg").write_bytes(b"\xff\xd8demo")
        return "demo.jpg"

    monkeypatch.setattr("app.catalog.service.CatalogService.item", item)
    monkeypatch.setattr("app.catalog.service.CatalogService.save_image", image)
    with Session(database) as session, session.begin():
        seed_users(session)
    return calls


def test_open_seed_reuses_snapshot_without_catalog(database, demo, monkeypatch):
    with Session(database) as session:
        lot_id, created = seed_open_lot(session)
        assert created
        lot = session.get(Lot, lot_id)
        now = session.scalar(select(func.clock_timestamp()))
        assert lot.starts_at < now < lot.ends_at
        assert lot.opening_bid_cents == 1000
        assert AuditService(session).verify(lot.id)["integrity"] == "valid"
        session.rollback()
        monkeypatch.setattr(
            "app.catalog.service.CatalogService.item",
            lambda *args: pytest.fail("Existing lot must survive source outage"),
        )
        assert seed_open_lot(session) == (lot_id, False)
        assert demo == [94979]


def test_expired_lot_preserved_and_new_open_lot_created(database, demo):
    with Session(database) as session:
        old_id, _ = seed_open_lot(session)
        old = session.get(Lot, old_id)
        old.ends_at = old.starts_at + timedelta(seconds=1)
        old.original_ends_at = old.ends_at
        session.commit()
        new_id, created = seed_open_lot(session)
        assert created and new_id != old_id
        assert session.scalar(select(func.count()).select_from(Lot)) == 2
        assert session.get(Lot, old_id).ends_at == old.ends_at


def test_seed_preserves_existing_account_and_balance(database, demo):
    with Session(database) as session:
        seller = session.scalar(
            select(User).where(User.email == "leiloeiro@example.com")
        )
        seller.active = False
        seller.password_hash = "preserved"
        wallet = session.scalar(select(Wallet).where(Wallet.user_id == seller.id))
        wallet.balance_cents = 1234
        session.commit()
        assert seed_users(session) == 0
        session.commit()
        with pytest.raises(HTTPException, match="409"):
            seed_open_lot(session)
        session.rollback()
        assert not seller.active and seller.password_hash == "preserved"
        assert wallet.balance_cents == 1234


def test_source_outage_keeps_users_without_partial_lot(database, demo, monkeypatch):
    def unavailable(*args):
        raise HTTPException(503, "Catálogo indisponível")

    monkeypatch.setattr("app.catalog.service.CatalogService.item", unavailable)
    with Session(database) as session:
        with pytest.raises(HTTPException, match="503"):
            seed_open_lot(session)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(User)) == 3
        assert session.scalar(select(func.count()).select_from(Lot)) == 0


def test_concurrent_seeds_import_only_one_lot(database, demo, monkeypatch):
    entered, release = Event(), Event()
    original = __import__(
        "app.catalog.service", fromlist=["CatalogService"]
    ).CatalogService.item

    def blocked(*args):
        entered.set()
        assert release.wait(10)
        return original(*args)

    monkeypatch.setattr("app.catalog.service.CatalogService.item", blocked)

    def run():
        with Session(database) as session:
            return seed_open_lot(session)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run)
        try:
            assert entered.wait(10)
            second = pool.submit(run)
        finally:
            release.set()
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert demo == [94979]


def test_existing_lot_with_missing_head_is_not_silently_reused(database, demo):
    with Session(database) as session:
        lot_id, _ = seed_open_lot(session)
        lot = session.get(Lot, lot_id)
        session.delete(session.get(AuditHead, lot.id))
        session.commit()
        with pytest.raises(HTTPException, match="409"):
            seed_open_lot(session)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Lot)) == 1
        assert session.get(AuditHead, lot.id) is None
