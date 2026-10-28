from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from uuid import uuid4

from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session
from test_bids_api import offer

from app.bids.service import BidService
from app.db.models import (
    AuditHead,
    Bid,
    Lot,
    OutboxEvent,
    Receipt,
    Settlement,
    User,
    Wallet,
    WalletEntry,
    WalletReservation,
)
from app.settlements.service import SettlementService
from app.worker import run_once


def expire(database, lot_id):
    with Session(database) as session, session.begin():
        lot = session.get(Lot, lot_id)
        lot.original_ends_at = lot.ends_at = session.scalar(
            select(func.clock_timestamp())
        ) - timedelta(milliseconds=1)


def test_settlement_capture_transfer_receipt_and_repeat(client, database, market):
    assert offer(client, market).status_code == 201
    expire(database, market["lots"][0])
    assert run_once(database) == (1, 0)
    assert run_once(database) == (0, 0)
    with Session(database) as session:
        assert not SettlementService(session).close(market["lots"][0])
        buyer = session.scalar(
            select(Wallet).where(Wallet.user_id == market["users"][1])
        )
        seller = session.scalar(
            select(Wallet).where(Wallet.user_id == market["users"][0])
        )
        assert (buyer.balance_cents, buyer.reserved_cents, buyer.available_cents) == (
            2000,
            0,
            2000,
        )
        assert seller.balance_cents == 18000
        assert session.scalar(select(func.sum(Wallet.balance_cents))) == 30000
        assert session.scalar(select(WalletReservation)).status == "captured"
        assert session.scalar(select(func.count()).select_from(Settlement)) == 1
        assert session.scalar(select(func.count()).select_from(Receipt)) == 1
        assert sorted(session.scalars(select(WalletEntry.type))) == [
            "credit",
            "debit",
            "reserve",
        ]
        receipt_id = session.scalar(select(Receipt.id))
        closed = session.scalar(
            select(OutboxEvent).where(OutboxEvent.event_type == "AuctionClosed")
        )
        assert closed.aggregate_version == 2 and closed.payload["sold"]
    response = client.get(f"/receipts/{receipt_id}")
    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["amount_cents"] == 8000
    assert set(snapshot) == {
        "id",
        "lot_id",
        "item_title",
        "image",
        "source_url",
        "item_attributes",
        "winner_public_id",
        "amount_cents",
        "currency",
        "settled_at",
    }
    assert "@example.com" not in response.text
    assert all(str(user_id) not in response.text for user_id in market["users"])
    assert offer(client, market, 9000, bidder=2).status_code == 409
    lot = client.get(f"/lots/{market['lots'][0]}").json()
    assert lot["closureComplete"] and lot["sold"] and lot["settledAmount"] == 8000
    assert lot["receiptId"] == str(receipt_id)
    assert (
        client.get("/auctioneers/me/summary", headers=market["headers"][0]).json()[
            "total_received_cents"
        ]
        == 8000
    )
    # Snapshot remains available independently of subsequent source/lot changes.
    with Session(database) as session, session.begin():
        session.get(
            Lot, market["lots"][0]
        ).item_title = "Changed directly in test database"
    assert client.get(f"/receipts/{receipt_id}").json() == snapshot


def test_no_bids_closes_without_any_money_or_receipt(client, database, market):
    expire(database, market["lots"][0])
    assert run_once(database) == (1, 0)
    with Session(database) as session:
        lot = session.get(Lot, market["lots"][0])
        assert lot.status == "closed" and lot.closed_at
        for model in (Settlement, Receipt, WalletEntry):
            assert session.scalar(select(func.count()).select_from(model)) == 0
    lot = client.get(f"/lots/{market['lots'][0]}").json()
    assert lot["closureComplete"] and not lot["sold"] and lot["receiptId"] is None


def test_unexpired_or_cancelled_lots_are_not_closed(client, database, market):
    assert run_once(database) == (0, 0)
    with Session(database) as session, session.begin():
        session.get(Lot, market["lots"][0]).status = "cancelled"
    expire(database, market["lots"][0])
    assert run_once(database) == (0, 0)
    with Session(database) as session:
        assert not SettlementService(session).close(market["lots"][0])


def test_failure_at_receipt_rolls_back_money_and_can_retry(client, database, market):
    assert offer(client, market).status_code == 201
    expire(database, market["lots"][0])

    def unavailable(*args):
        raise RuntimeError("simulated receipt failure")

    event.listen(Receipt, "before_insert", unavailable)
    try:
        assert run_once(database) == (0, 1)
        with Session(database) as session:
            assert session.scalar(select(func.count()).select_from(Settlement)) == 0
            assert session.scalar(select(WalletReservation)).status == "active"
            buyer = session.scalar(
                select(Wallet).where(Wallet.user_id == market["users"][1])
            )
            assert buyer.balance_cents == 10000 and buyer.reserved_cents == 8000
            assert session.scalar(select(func.count()).select_from(WalletEntry)) == 1
            assert session.get(Lot, market["lots"][0]).status != "closed"
    finally:
        event.remove(Receipt, "before_insert", unavailable)
    assert run_once(database) == (1, 0)


def test_two_workers_cannot_charge_twice(client, database, market):
    assert offer(client, market).status_code == 201
    expire(database, market["lots"][0])
    barrier = Barrier(2)

    def close(_):
        with Session(database) as session:
            barrier.wait(timeout=10)
            return SettlementService(session).close(market["lots"][0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(close, [0, 1])) == [False, True]
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Settlement)) == 1
        assert session.scalar(select(func.count()).select_from(Receipt)) == 1
        assert session.scalar(select(func.count()).select_from(WalletEntry)) == 3


def test_bad_winner_is_not_charged_and_other_lots_continue(client, database, market):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        session.get(AuditHead, market["lots"][0]).signature = "0" * 64
    for lot_id in market["lots"]:
        expire(database, lot_id)
    assert run_once(database) == (1, 1)
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(Settlement)) == 0
        assert session.scalar(select(WalletReservation)).status == "active"
        assert session.get(Lot, market["lots"][1]).status == "closed"


def test_capture_preserves_other_lot_reserves(client, database, market):
    with Session(database) as session, session.begin():
        session.get(Lot, market["lots"][1]).opening_bid_cents = 1000
    assert offer(client, market).status_code == 201
    assert offer(client, market, 1000, lot=1).status_code == 201
    expire(database, market["lots"][0])
    assert run_once(database) == (1, 0)
    wallet = client.get("/wallets/me", headers=market["headers"][1]).json()
    assert (
        wallet["balance_cents"],
        wallet["reserved_cents"],
        wallet["available_cents"],
    ) == (2000, 1000, 1000)


def test_worker_does_not_close_a_bid_that_is_committing_extension(
    client, database, market
):
    ready, release = Event(), Event()
    with Session(database) as session, session.begin():
        lot = session.get(Lot, market["lots"][0])
        deadline = session.scalar(select(func.clock_timestamp())) + timedelta(seconds=1)
        lot.original_ends_at = lot.ends_at = deadline

    def hold_bid(*args):
        ready.set()
        assert release.wait(timeout=10)

    def bid():
        with Session(database) as session:
            return BidService(session).place(
                market["lots"][0], market["users"][1], 8000
            )

    event.listen(Bid, "before_insert", hold_bid)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(bid)
            try:
                assert ready.wait(timeout=10)
                with database.connect() as connection:
                    connection.execute(
                        text(
                            "SELECT pg_sleep(GREATEST(0, EXTRACT(EPOCH FROM "
                            "CAST(:deadline AS timestamptz) - "
                            "clock_timestamp())) + 0.02)"
                        ),
                        {"deadline": deadline},
                    )
                assert run_once(database) == (0, 0)
            finally:
                release.set()
            assert future.result(timeout=10).extended
    finally:
        event.remove(Bid, "before_insert", hold_bid)
    assert run_once(database) == (0, 0)
    with Session(database) as session:
        assert session.get(Lot, market["lots"][0]).status == "live"
        assert session.scalar(select(func.count()).select_from(Settlement)) == 0


def test_participations_are_private_and_receipt_is_public(client, database, market):
    assert offer(client, market).status_code == 201
    assert offer(client, market, 9000, bidder=2).status_code == 201
    expire(database, market["lots"][0])
    assert run_once(database) == (1, 0)
    path = "/bidders/me/participations"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=market["headers"][0]).status_code == 403
    loser = client.get(path, headers=market["headers"][1]).json()
    winner = client.get(path, headers=market["headers"][2]).json()
    assert len(loser) == len(winner) == 1
    assert not loser[0]["won"] and loser[0]["receipt_id"] is None
    assert winner[0]["won"] and winner[0]["receipt_id"]
    assert not winner[0]["leading"]
    assert client.get(f"/receipts/{winner[0]['receipt_id']}").status_code == 200
    assert client.get(f"/receipts/{uuid4()}").status_code == 404
    assert client.get(path + "?offset=100", headers=market["headers"][2]).json() == []


def test_inactive_winner_is_still_settled(client, database, market):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        session.get(User, market["users"][1]).active = False
    expire(database, market["lots"][0])
    assert run_once(database) == (1, 0)
