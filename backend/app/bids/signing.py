"""Canonical records for the future public audit; never sign personal data."""

import hashlib
import hmac
import json
from datetime import UTC

from fastapi import HTTPException

from app.config import get_settings

ZERO_HASH = "0" * 64
KEY_VERSION = 1


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sign(value: dict) -> str:
    secret = get_settings().audit_secret
    if secret is None:
        raise HTTPException(503, "Assinatura de lances indisponível")
    return hmac.new(
        secret.get_secret_value().encode(), canonical(value), hashlib.sha256
    ).hexdigest()


def record(bid, public_id) -> dict:
    return {
        "lot_id": str(bid.lot_id),
        "bid_id": str(bid.id),
        "sequence": bid.sequence,
        "bidder_public_id": str(public_id),
        "amount_cents": bid.amount_cents,
        "accepted_at": bid.accepted_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "previous_hash": bid.previous_hash,
        "key_version": bid.key_version,
    }


def head_record(lot_id, sequence, last_hash) -> dict:
    return {
        "kind": "audit_head",
        "lot_id": str(lot_id),
        "last_sequence": sequence,
        "last_hash": last_hash,
        "key_version": KEY_VERSION,
    }
