from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.bids.service import BidService
from app.bids.signing import canonical, record, sign
from app.db.models import (
    AuditHead,
    Bid,
    Lot,
    OutboxEvent,
    User,
    Wallet,
    WalletEntry,
    WalletReservation,
)


def offer(client, market, amount=8000, bidder=1, lot=0):
    return client.post(
        f"/lots/{market['lots'][lot]}/bids",
        headers=market["headers"][bidder],
        json={"amount_cents": amount},
    )


def test_bid_reserve_outbid_release_history_privacy(client, database, market):
    first = offer(client, market)
    assert first.status_code == 201, first.text
    assert first.json()["sequence"] == 1
    assert not first.json()["extended"]
    second = offer(client, market, 9000, 2)
    assert second.status_code == 201, second.text
    assert second.json()["sequence"] == 2
    balances = [
        client.get("/wallets/me", headers=h).json() for h in market["headers"][1:]
    ]
    assert [w["balance_cents"] for w in balances] == [10000, 10000]
    assert [w["reserved_cents"] for w in balances] == [0, 9000]
    assert [w["available_cents"] for w in balances] == [10000, 1000]
    path = f"/lots/{market['lots'][0]}/bids"
    history = client.get(path)
    assert [b["amount_cents"] for b in history.json()] == [8000, 9000]
    assert client.get(path + "?after=1").json() == [history.json()[1]]
    assert set(history.json()[0]) == {
        "id",
        "bidder_public_id",
        "sequence",
        "amount_cents",
        "accepted_at",
    }
    assert "@example.com" not in history.text
    assert all(str(uid) not in history.text for uid in market["users"])
    with Session(database) as session:
        reservations = session.scalars(
            select(WalletReservation).order_by(WalletReservation.created_at)
        ).all()
        assert [r.status for r in reservations] == ["released", "active"]
        assert session.scalar(select(func.count()).select_from(WalletEntry)) == 3
        events = session.scalars(select(OutboxEvent)).all()
        assert len(events) == 2
        assert all(e.published_at is None for e in events)
        bid = session.get(Bid, second.json()["id"])
        public_id = session.get(User, market["users"][2]).public_id
        import hashlib

        assert (
            bid.record_hash
            == hashlib.sha256(canonical(record(bid, public_id))).hexdigest()
        )
        assert bid.signature == sign({"kind": "bid", "record_hash": bid.record_hash})
        assert session.get(AuditHead, market["lots"][0]).last_hash == bid.record_hash
    lot = client.get(f"/lots/{market['lots'][0]}").json()
    assert lot["currentBid"] == 9000 and lot["bids"] == 2
    assert (
        client.delete(
            f"/lots/{market['lots'][0]}", headers=market["headers"][0]
        ).status_code
        == 409
    )


@pytest.mark.parametrize("amount", [0, -1, True, 8000.5, "8000", 10**12 + 1])
def test_bid_requires_positive_integer(client, market, amount):
    assert offer(client, market, amount).status_code == 422


def test_business_rejections_leave_no_side_effects(client, database, market):
    path = f"/lots/{market['lots'][0]}/bids"
    assert client.post(path, json={"amount_cents": 8000}).status_code == 401
    assert offer(client, market, bidder=0).status_code == 403
    assert "mínimo" in offer(client, market, 7999).json()["detail"]
    assert "insuficiente" in offer(client, market, 10001).json()["detail"]
    assert offer(client, market).status_code == 201
    assert "ganhando" in offer(client, market, 9000).json()["detail"]
    assert "mínimo" in offer(client, market, 8999, 2).json()["detail"]
    assert offer(client, market, 9000, lot=1).status_code == 409
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Bid)) == 1
        assert session.scalar(select(func.count()).select_from(WalletEntry)) == 1
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 1


@pytest.mark.parametrize("state", ["scheduled", "expired", "closed", "cancelled"])
def test_only_live_lots_accept_bids(client, database, market, state):
    with Session(database) as session, session.begin():
        lot = session.get(Lot, market["lots"][0])
        now = session.scalar(select(func.clock_timestamp()))
        if state == "scheduled":
            lot.starts_at = now + timedelta(minutes=10)
        elif state == "expired":
            lot.original_ends_at = lot.ends_at = now - timedelta(seconds=1)
        else:
            lot.status = state
            if state == "closed":
                lot.closed_at = now
    response = offer(client, market)
    assert response.status_code == 409
    assert (
        "iniciado" in response.text
        if state == "scheduled"
        else "encerrado" in response.text
    )


def test_anti_sniping_and_events_are_atomic(client, database, market):
    with Session(database) as session, session.begin():
        lot = session.get(Lot, market["lots"][0])
        original = session.scalar(select(func.clock_timestamp())) + timedelta(
            seconds=30
        )
        lot.original_ends_at = lot.ends_at = original
    response = offer(client, market)
    assert response.status_code == 201, response.text
    data = response.json()
    from datetime import datetime

    assert data["extended"]
    assert datetime.fromisoformat(data["ends_at"]) - datetime.fromisoformat(
        data["accepted_at"]
    ) == timedelta(seconds=120)
    with Session(database) as session:
        lot = session.get(Lot, market["lots"][0])
        assert lot.original_ends_at == original
        assert lot.ends_at > original
        assert {e.event_type for e in session.scalars(select(OutboxEvent))} == {
            "BidAccepted",
            "AuctionExtended",
        }


def test_failure_after_release_rolls_back_everything(client, database, market):
    assert offer(client, market).status_code == 201

    def fail_outbox(mapper, connection, target):
        raise RuntimeError("simulated storage failure")

    event.listen(OutboxEvent, "before_insert", fail_outbox)
    try:
        with Session(database) as session, pytest.raises(RuntimeError):
            BidService(session).place(market["lots"][0], market["users"][2], 9000)
    finally:
        event.remove(OutboxEvent, "before_insert", fail_outbox)
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Bid)) == 1
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 1
        assert session.scalar(select(func.count()).select_from(WalletEntry)) == 1
        reservation = session.scalar(select(WalletReservation))
        assert reservation.status == "active" and reservation.amount_cents == 8000
        assert session.get(AuditHead, market["lots"][0]).last_sequence == 1
        wallets = session.scalars(select(Wallet).order_by(Wallet.user_id)).all()
        assert sum(w.reserved_cents for w in wallets) == 8000


@pytest.mark.parametrize("same_wallet", [False, True])
def test_concurrent_bids_cannot_double_reserve(client, database, market, same_wallet):
    barrier = Barrier(2)

    def compete(index):
        with Session(database) as session:
            barrier.wait(timeout=10)
            try:
                result = BidService(session).place(
                    market["lots"][index if same_wallet else 0],
                    market["users"][1 if same_wallet else index + 1],
                    8000,
                )
                return result.amount_cents
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(compete, [0, 1]))
    assert sorted(results) == [409, 8000]
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Bid)) == 1
        assert session.scalar(select(func.count()).select_from(WalletReservation)) == 1
        wallets = session.scalars(select(Wallet)).all()
        assert sum(w.reserved_cents for w in wallets) == 8000
        assert all(0 <= w.reserved_cents <= w.balance_cents for w in wallets)


def test_deadline_is_rechecked_after_waiting_for_wallet(client, database, market):
    from threading import Event

    from sqlalchemy import text

    waiting = Event()

    def wallet_query(connection, cursor, statement, parameters, context, executemany):
        if "FROM wallets" in statement and "FOR UPDATE" in statement:
            waiting.set()

    with Session(database) as blocker:
        lot = blocker.get(Lot, market["lots"][0])
        deadline = blocker.scalar(select(func.clock_timestamp())) + timedelta(seconds=1)
        lot.original_ends_at = lot.ends_at = deadline
        blocker.commit()
        blocker.scalar(
            select(Wallet).where(Wallet.user_id == market["users"][1]).with_for_update()
        )
        event.listen(database, "before_cursor_execute", wallet_query)

        def attempt():
            with Session(database) as session:
                try:
                    BidService(session).place(
                        market["lots"][0], market["users"][1], 8000
                    )
                except HTTPException as error:
                    return error.status_code, error.detail

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(attempt)
            try:
                assert waiting.wait(timeout=10)
                blocker.execute(
                    text(
                        "SELECT pg_sleep(GREATEST(0, EXTRACT(EPOCH FROM "
                        "CAST(:deadline AS timestamptz) - clock_timestamp())) + 0.02)"
                    ),
                    {"deadline": deadline},
                )
            finally:
                blocker.rollback()
                event.remove(database, "before_cursor_execute", wallet_query)
            status, detail = future.result(timeout=10)
            assert status == 409 and "encerrado" in detail
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Bid)) == 0


def test_missing_signing_key_cannot_partially_accept(
    client, database, market, monkeypatch
):
    from app.config import get_settings

    monkeypatch.setenv("AUDIT_SECRET", "")
    get_settings.cache_clear()
    try:
        assert offer(client, market).status_code == 503
        with Session(database) as session:
            assert session.scalar(select(func.count()).select_from(Bid)) == 0
            assert session.scalar(select(func.count()).select_from(AuditHead)) == 2
            assert sum(session.scalars(select(Wallet.reserved_cents))) == 0
    finally:
        get_settings.cache_clear()


def test_inactive_user_and_missing_lot_are_rejected(client, database, market):
    assert (
        client.post(
            f"/lots/{uuid4()}/bids",
            headers=market["headers"][1],
            json={"amount_cents": 8000},
        ).status_code
        == 404
    )
    with Session(database) as session, session.begin():
        session.get(User, market["users"][1]).active = False
    assert offer(client, market).status_code == 401
