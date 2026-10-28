from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_users_api import login, register

from app.catalog.service import CatalogService
from app.db.models import Bid, WalletEntry


def lot_data():
    now = datetime.now(UTC)
    return {
        "external_item_id": 94979,
        "category": "fine-art",
        "opening_bid_cents": 10000,
        "min_increment_cents": 1000,
        "starts_at": (now + timedelta(hours=1)).isoformat(),
        "ends_at": (now + timedelta(hours=2)).isoformat(),
    }


@pytest.fixture
def external(monkeypatch):
    monkeypatch.setattr(
        CatalogService,
        "item",
        lambda self, item_id: {
            "id": item_id,
            "title": "Retrato público",
            "url": "https://clevelandart.org/art/1915.534",
            "technique": "óleo",
            "share_license_status": "CC0",
        },
    )
    monkeypatch.setattr(CatalogService, "save_image", lambda self, item: "test.jpg")


def test_lot_crud_ownership_snapshot_and_cancellation(client, external, monkeypatch):
    register(client, "seller@example.com", "auctioneer")
    register(client, "other@example.com", "auctioneer")
    headers = login(client, "seller@example.com")
    created = client.post("/lots", headers=headers, json=lot_data())
    assert created.status_code == 201, created.text
    lot = created.json()
    assert lot["title"] == "Retrato público"
    assert lot["image"] == "/api/media/test.jpg"
    assert client.get("/lots").json()[0]["id"] == lot["id"]
    assert client.get("/lots?category=fine-art&q=público").json()[0]["id"] == lot["id"]
    assert (
        client.get("/lots/mine", headers=login(client, "other@example.com")).json()
        == []
    )
    assert (
        client.patch(
            f"/lots/{lot['id']}",
            headers=login(client, "other@example.com"),
            json={"opening_bid_cents": 20000},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/lots/{lot['id']}", headers=headers, json={"opening_bid_cents": 20000}
        ).json()["currentBid"]
        == 20000
    )

    def unavailable(self, item_id):
        raise HTTPException(503, "Serviço indisponível")

    monkeypatch.setattr(CatalogService, "item", unavailable)
    assert client.get(f"/lots/{lot['id']}").status_code == 200
    assert client.post("/lots", headers=headers, json=lot_data()).status_code == 503
    assert client.delete(f"/lots/{lot['id']}", headers=headers).status_code == 204
    assert client.get(f"/lots/{lot['id']}").status_code == 404
    assert client.get("/lots").json() == []
    assert client.get("/lots/mine", headers=headers).json()[0]["status"] == "cancelled"


def test_bidder_cannot_manage_lots(client, external):
    register(client)
    headers = login(client)
    assert client.post("/lots", headers=headers, json=lot_data()).status_code == 403
    assert client.get("/lots/mine", headers=headers).status_code == 403
    assert client.get("/catalog/items", headers=headers).status_code == 403
    assert client.post("/lots", json=lot_data()).status_code == 401


def test_lot_with_bid_cannot_be_cancelled(client, external, database):
    seller = register(client, "seller@example.com", "auctioneer").json()
    bidder = register(client).json()
    headers = login(client, seller["email"])
    lot = client.post("/lots", headers=headers, json=lot_data()).json()
    with Session(database) as session, session.begin():
        session.add(
            Bid(
                lot_id=lot["id"],
                bidder_id=bidder["id"],
                sequence=1,
                amount_cents=10000,
                previous_hash="0" * 64,
                record_hash="a" * 64,
                signature="b" * 64,
                key_version=1,
            )
        )
    assert client.delete(f"/lots/{lot['id']}", headers=headers).status_code == 409
    assert (
        client.patch(
            f"/lots/{lot['id']}", headers=headers, json={"opening_bid_cents": 20000}
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "change",
    [
        {"opening_bid_cents": -1},
        {"category": "invalid"},
        {"starts_at": "invalid"},
        {"external_item_id": "https://evil.test"},
    ],
)
def test_invalid_lot_is_rejected(client, external, change):
    register(client, "seller@example.com", "auctioneer")
    assert (
        client.post(
            "/lots",
            headers=login(client, "seller@example.com"),
            json={**lot_data(), **change},
        ).status_code
        == 422
    )


def test_deposit_idempotency_and_private_ledger(client, database):
    register(client)
    register(client, "other@example.com")
    headers = {**login(client), "Idempotency-Key": str(uuid4())}
    body = {"amount_cents": 10000}
    first = client.post("/wallets/me/deposits", headers=headers, json=body)
    assert first.status_code == 200, first.text
    assert first.json()["available_cents"] == 10000
    assert (
        client.post("/wallets/me/deposits", headers=headers, json=body).json()[
            "balance_cents"
        ]
        == 10000
    )
    assert (
        client.post(
            "/wallets/me/deposits", headers=headers, json={"amount_cents": 20000}
        ).status_code
        == 409
    )
    assert len(client.get("/wallets/me/entries", headers=headers).json()) == 1
    assert (
        client.get(
            "/wallets/me/entries", headers=login(client, "other@example.com")
        ).json()
        == []
    )
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(WalletEntry)) == 1


def test_deposit_requires_bidder_and_positive_amount(client):
    register(client, "seller@example.com", "auctioneer")
    assert (
        client.post(
            "/wallets/me/deposits",
            headers={
                **login(client, "seller@example.com"),
                "Idempotency-Key": str(uuid4()),
            },
            json={"amount_cents": 100},
        ).status_code
        == 403
    )
    register(client)
    headers = {**login(client), "Idempotency-Key": str(uuid4())}
    assert (
        client.post(
            "/wallets/me/deposits", headers=headers, json={"amount_cents": -1}
        ).status_code
        == 422
    )
