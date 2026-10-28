from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from test_bids_api import offer

from app.audit.checkpoints import checkpoint_batch, initialize_empty_heads
from app.audit.journal import Journal, JournalError
from app.bids.signing import ZERO_HASH
from app.db.models import AuditHead, Bid, Lot, User, WalletEntry, WalletReservation


def audit(client, market):
    return client.get(f"/lots/{market['lots'][0]}/audit")


def test_empty_history_is_authenticated_and_anchored(client, database, market):
    first = audit(client, market)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["integrity"] == "valid"
    assert first.json()["verified_count"] == 0
    assert first.json()["checkpoint_status"] == "pending"
    _, written, failed = checkpoint_batch(database)
    assert written == 2 and failed == 0
    assert audit(client, market).json()["checkpoint_status"] == "anchored"
    assert checkpoint_batch(database)[1:] == (0, 0)


def test_missing_empty_head_is_invalid_until_explicit_bootstrap(
    client, database, market
):
    with Session(database) as session, session.begin():
        session.delete(session.get(AuditHead, market["lots"][0]))
    assert audit(client, market).json()["integrity"] == "invalid"
    assert offer(client, market).status_code == 409
    assert initialize_empty_heads(database) == 1
    assert initialize_empty_heads(database) == 0
    assert audit(client, market).json()["integrity"] == "valid"


def test_real_chain_checkpoint_and_public_privacy(client, database, market):
    assert offer(client, market).status_code == 201
    assert checkpoint_batch(database)[2] == 0
    assert offer(client, market, 9000, bidder=2).status_code == 201
    assert audit(client, market).json()["checkpoint_status"] == "pending"
    assert checkpoint_batch(database)[2] == 0
    response = audit(client, market)
    data = response.json()
    assert data["integrity"] == "valid" and data["checkpoint_status"] == "anchored"
    assert data["verified_count"] == data["checkpoint_sequence"] == 2
    assert [entry["sequence"] for entry in data["history"]] == [1, 2]
    assert all(str(uid) not in response.text for uid in market["users"])
    assert "@example.com" not in response.text
    second_page = client.get(f"/lots/{market['lots'][0]}/audit?after=1").json()
    assert len(second_page["history"]) == 1 and second_page["verified_count"] == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount_cents", 8100),
        ("record_hash", "f" * 64),
        ("previous_hash", "f" * 64),
        ("signature", "f" * 64),
        ("sequence", 4),
    ],
)
def test_direct_bid_tampering_is_detected(client, database, market, field, value):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        setattr(session.scalar(select(Bid)), field, value)
    assert audit(client, market).json()["integrity"] == "invalid"
    assert offer(client, market, 10000, bidder=2).status_code == 409


def test_tail_removal_and_forged_insertion_are_detected(client, database, market):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        session.get(Lot, market["lots"][0]).current_bid_id = None
        session.flush()
        session.execute(delete(WalletEntry))
        session.execute(delete(WalletReservation))
        session.execute(delete(Bid))
    assert audit(client, market).json()["integrity"] == "invalid"
    # Plausible hashes alone cannot authenticate a newly inserted row.
    with Session(database) as session, session.begin():
        session.add(
            Bid(
                lot_id=market["lots"][0],
                bidder_id=market["users"][1],
                sequence=1,
                amount_cents=8000,
                previous_hash=ZERO_HASH,
                record_hash="a" * 64,
                signature="b" * 64,
                key_version=1,
            )
        )
    assert audit(client, market).json()["integrity"] == "invalid"


def test_database_rollback_with_valid_old_signatures_is_detected_by_external_checkpoint(
    client, database, market
):
    assert offer(client, market).status_code == 201
    with Session(database) as session:
        head = session.get(AuditHead, market["lots"][0])
        old = {
            name: getattr(head, name)
            for name in ["last_sequence", "last_hash", "signature", "key_version"]
        }
        first_id = session.scalar(select(Bid.id))
    checkpoint_batch(database)
    assert offer(client, market, 9000, bidder=2).status_code == 201
    checkpoint_batch(database)
    with Session(database) as session, session.begin():
        lot = session.get(Lot, market["lots"][0])
        second_id = lot.current_bid_id
        lot.current_bid_id = first_id
        session.flush()
        session.execute(delete(WalletEntry).where(WalletEntry.bid_id == second_id))
        session.execute(
            delete(WalletReservation).where(WalletReservation.bid_id == second_id)
        )
        session.execute(delete(Bid).where(Bid.id == second_id))
        head = session.get(AuditHead, lot.id)
        for name, value in old.items():
            setattr(head, name, value)
    data = audit(client, market).json()
    assert data["integrity"] == "invalid"
    assert data["checkpoint_sequence"] == 2 and data["verified_count"] == 1
    assert any("checkpoint externo" in item for item in data["issues"])
    assert checkpoint_batch(database)[2] == 1


def test_checkpoint_corruption_or_partial_append_is_not_silently_repaired(
    client, database, market
):
    checkpoint_batch(database)
    path = Journal().path(market["lots"][0])
    with path.open("a") as stream:
        stream.write("{incomplete")
    data = audit(client, market).json()
    assert data["integrity"] == "invalid" and data["checkpoint_status"] == "invalid"
    with pytest.raises(JournalError):
        Journal().append(market["lots"][0], 0, ZERO_HASH)
    assert checkpoint_batch(database)[2] == 1


def test_initial_head_signature_and_public_identifier_tampering(
    client, database, market
):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        session.get(User, market["users"][1]).public_id = uuid4()
    assert audit(client, market).json()["integrity"] == "invalid"


def test_bootstrap_never_resigns_existing_bids(client, database, market):
    assert offer(client, market).status_code == 201
    with Session(database) as session, session.begin():
        session.delete(session.get(AuditHead, market["lots"][0]))
    assert initialize_empty_heads(database) == 0
    assert audit(client, market).json()["integrity"] == "invalid"


def test_deleted_journal_reports_pending_instead_of_fully_anchored(
    client, database, market
):
    checkpoint_batch(database)
    Journal().path(market["lots"][0]).unlink()
    data = audit(client, market).json()
    assert data["integrity"] == "valid" and data["checkpoint_status"] == "pending"


def test_unavailable_checkpoint_storage_is_not_a_valid_result(
    client, market, monkeypatch
):
    def unavailable(self, lot_id):
        raise PermissionError("unavailable")

    monkeypatch.setattr(Journal, "read", unavailable)
    data = audit(client, market).json()
    assert (
        data["integrity"] == "unavailable"
        and data["checkpoint_status"] == "unavailable"
    )


def test_unknown_lot_returns_404(client):
    assert client.get(f"/lots/{uuid4()}/audit").status_code == 404


def test_removing_middle_bid_breaks_the_chain(client, database, market):
    assert offer(client, market).status_code == 201
    middle_id = offer(client, market, 9000, bidder=2).json()["id"]
    assert offer(client, market, 10000, bidder=1).status_code == 201
    with Session(database) as session, session.begin():
        session.execute(delete(WalletEntry).where(WalletEntry.bid_id == middle_id))
        session.execute(
            delete(WalletReservation).where(WalletReservation.bid_id == middle_id)
        )
        session.execute(delete(Bid).where(Bid.id == middle_id))
    assert audit(client, market).json()["integrity"] == "invalid"


def test_checkpoint_chain_detects_middle_record_removal(client, database, market):
    checkpoint_batch(database)
    assert offer(client, market).status_code == 201
    checkpoint_batch(database)
    assert offer(client, market, 9000, bidder=2).status_code == 201
    checkpoint_batch(database)
    path = Journal().path(market["lots"][0])
    lines = path.read_text().splitlines(keepends=True)
    assert len(lines) == 3
    path.write_text(lines[0] + lines[2])
    assert audit(client, market).json()["checkpoint_status"] == "invalid"


def test_invalid_journal_encoding_is_reported_as_integrity_failure(
    client, database, market
):
    checkpoint_batch(database)
    path = Journal().path(market["lots"][0])
    path.write_bytes(b"\xff\xfe\xff")
    assert audit(client, market).json()["integrity"] == "invalid"
