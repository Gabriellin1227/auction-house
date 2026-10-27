from datetime import UTC, datetime, timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from conftest import migrate
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.db.base import Base
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


def make_lot(session):
    seller = User(
        name="Seller",
        email="seller@example.test",
        password_hash="test",
        role="auctioneer",
    )
    bidder = User(
        name="Bidder", email="bidder@example.test", password_hash="test", role="bidder"
    )
    session.add_all([seller, bidder])
    session.flush()
    seller_wallet = Wallet(user_id=seller.id)
    wallet = Wallet(user_id=bidder.id, balance_cents=10000)
    now = datetime.now(UTC)
    lot = Lot(
        seller_id=seller.id,
        source_provider="test",
        external_item_id="item-1",
        source_url="https://example.test/items/1",
        item_title="Test item",
        local_image_key="test/item.webp",
        opening_bid_cents=100,
        min_increment_cents=10,
        starts_at=now - timedelta(minutes=1),
        original_ends_at=now + timedelta(minutes=10),
        ends_at=now + timedelta(minutes=10),
        status="live",
    )
    session.add_all([seller_wallet, wallet, lot])
    session.flush()
    return lot, bidder, wallet, seller_wallet


def make_bid(session, lot, bidder, sequence=1):
    bid = Bid(
        lot_id=lot.id,
        bidder_id=bidder.id,
        sequence=sequence,
        amount_cents=100,
        previous_hash="0" * 64,
        record_hash="a" * 64,
        signature="b" * 64,
        key_version=1,
    )
    session.add(bid)
    session.flush()
    return bid


def test_migrations_roundtrip_and_match_models(empty_database):
    migrate(empty_database)
    assert set(inspect(empty_database).get_table_names()) == set(
        Base.metadata.tables
    ) | {"alembic_version"}
    with empty_database.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
    migrate(empty_database, "base", downgrade=True)
    assert set(inspect(empty_database).get_table_names()) <= {"alembic_version"}
    migrate(empty_database)
    # A second upgrade must be harmless.
    migrate(empty_database)
    assert "outbox_events" in inspect(empty_database).get_table_names()


@pytest.mark.parametrize("balance,reserved", [(-1, 0), (100, -1), (100, 101)])
def test_wallet_rejects_invalid_balance(session, balance, reserved):
    _, _, wallet, _ = make_lot(session)
    wallet.balance_cents = balance
    wallet.reserved_cents = reserved
    with pytest.raises(IntegrityError):
        session.flush()


def test_email_must_be_normalized_and_unique(session):
    make_lot(session)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            User(
                name="Other",
                email=" Seller@Example.Test ",
                password_hash="x",
                role="bidder",
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            User(
                name="Other",
                email="seller@example.test",
                password_hash="x",
                role="bidder",
            )
        )
        session.flush()


@pytest.mark.parametrize(
    "field,value",
    [("opening_bid_cents", 0), ("min_increment_cents", -1), ("status", "invalid")],
)
def test_lot_rejects_invalid_prices_or_status(session, field, value):
    lot, *_ = make_lot(session)
    setattr(lot, field, value)
    with pytest.raises(IntegrityError):
        session.flush()


def test_lot_rejects_invalid_period(session):
    lot, *_ = make_lot(session)
    lot.ends_at = lot.starts_at
    with pytest.raises(IntegrityError):
        session.flush()


def test_current_bid_cannot_reference_another_lot(session):
    lot, bidder, *_ = make_lot(session)
    bid = make_bid(session, lot, bidder)
    other = Lot(
        seller_id=lot.seller_id,
        source_provider="test",
        external_item_id="item-2",
        source_url=lot.source_url,
        item_title="Other",
        local_image_key="other.webp",
        opening_bid_cents=100,
        min_increment_cents=10,
        starts_at=lot.starts_at,
        original_ends_at=lot.original_ends_at,
        ends_at=lot.ends_at,
        current_bid_id=bid.id,
    )
    session.add(other)
    with pytest.raises(IntegrityError):
        session.flush()


def test_only_one_active_reservation_per_lot(session):
    lot, bidder, wallet, _ = make_lot(session)
    first = make_bid(session, lot, bidder)
    second = make_bid(session, lot, bidder, 2)
    session.add(
        WalletReservation(
            lot_id=lot.id, wallet_id=wallet.id, bid_id=first.id, amount_cents=100
        )
    )
    session.flush()
    session.add(
        WalletReservation(
            lot_id=lot.id, wallet_id=wallet.id, bid_id=second.id, amount_cents=100
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_bid_sequence_cannot_be_reused(session):
    lot, bidder, *_ = make_lot(session)
    make_bid(session, lot, bidder)
    with pytest.raises(IntegrityError):
        make_bid(session, lot, bidder)


def test_financial_operation_key_prevents_duplicate_deposits(session):
    _, _, wallet, _ = make_lot(session)
    for _ in range(2):
        session.add(
            WalletEntry(
                wallet_id=wallet.id,
                type="deposit",
                amount_cents=100,
                operation_key="deposit:user:key",
                request_hash="a" * 64,
            )
        )
        if _ == 0:
            session.flush()
        else:
            with pytest.raises(IntegrityError):
                session.flush()


def test_lot_settlement_and_receipt_are_unique(session):
    lot, bidder, wallet, seller_wallet = make_lot(session)
    bid = make_bid(session, lot, bidder)
    settlement = Settlement(
        lot_id=lot.id,
        winning_bid_id=bid.id,
        buyer_wallet_id=wallet.id,
        seller_wallet_id=seller_wallet.id,
        amount_cents=100,
    )
    session.add(settlement)
    session.flush()
    session.add(Receipt(settlement_id=settlement.id, snapshot={"amount_cents": 100}))
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Receipt(settlement_id=settlement.id, snapshot={}))
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Settlement(
                lot_id=lot.id,
                winning_bid_id=bid.id,
                buyer_wallet_id=wallet.id,
                seller_wallet_id=seller_wallet.id,
                amount_cents=100,
            )
        )
        session.flush()


def test_wallet_changes_and_outbox_rollback_together(session):
    lot, _, wallet, _ = make_lot(session)
    session.commit()
    wallet_id = wallet.id
    wallet.balance_cents = 9000
    session.add(
        OutboxEvent(
            lot_id=lot.id,
            aggregate_version=1,
            event_type="BidAccepted",
            payload={"amount_cents": 1000},
        )
    )
    session.flush()
    session.rollback()
    assert session.get(Wallet, wallet_id).balance_cents == 10000
    assert session.scalars(select(OutboxEvent)).all() == []


def test_referenced_users_cannot_be_deleted(session):
    _, bidder, *_ = make_lot(session)
    session.delete(bidder)
    with pytest.raises(IntegrityError):
        session.flush()


def test_audit_header_rejects_invalid_hash(session):
    lot, *_ = make_lot(session)
    session.add(
        AuditHead(
            lot_id=lot.id,
            last_sequence=0,
            last_hash="invalid",
            signature="b" * 64,
            key_version=1,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_database_row_lock_serializes_wallet_updates(database):
    # A competing transaction must not update an already locked wallet.
    with database.begin() as connection:
        connection.execute(
            text("CREATE TABLE lock_probe (id int primary key, balance bigint)")
        )
        connection.execute(text("INSERT INTO lock_probe VALUES (1, 100)"))
    with database.connect() as first, database.connect() as second:
        first.execute(text("SELECT * FROM lock_probe WHERE id = 1 FOR UPDATE"))
        second.execute(text("SET LOCAL lock_timeout = '100ms'"))
        from sqlalchemy.exc import OperationalError

        with pytest.raises(OperationalError) as error:
            second.execute(text("UPDATE lock_probe SET balance = 0 WHERE id = 1"))
        assert error.value.orig.sqlstate == "55P03"
        first.rollback()
        second.rollback()
