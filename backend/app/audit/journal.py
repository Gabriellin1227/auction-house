"""Signed append-only checkpoint journal, independent of PostgreSQL data files."""

import fcntl
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.bids.signing import KEY_VERSION, ZERO_HASH, canonical, sign
from app.config import get_settings


class JournalError(ValueError):
    pass


def decode(lines, lot_id):
    records = []
    previous = ZERO_HASH
    sequence = -1
    for line in lines:
        try:
            value = json.loads(line)
            payload = {
                key: value[key]
                for key in (
                    "lot_id",
                    "sequence",
                    "last_hash",
                    "previous_checkpoint_hash",
                    "created_at",
                    "key_version",
                )
            }
            digest = hashlib.sha256(canonical(payload)).hexdigest()
            if (
                value["lot_id"] != str(lot_id)
                or type(value["sequence"]) is not int
                or value["sequence"] <= sequence
                or value["previous_checkpoint_hash"] != previous
                or value["key_version"] != KEY_VERSION
                or not hmac.compare_digest(value["checkpoint_hash"], digest)
                or not hmac.compare_digest(
                    value["signature"],
                    sign({"kind": "checkpoint", "checkpoint_hash": digest}),
                )
            ):
                raise JournalError("Checkpoint inválido")
            records.append(value)
            previous = digest
            sequence = value["sequence"]
        except (KeyError, ValueError, TypeError) as error:
            raise JournalError("Journal inválido ou incompleto") from error
    return records


class Journal:
    def __init__(self, root: Path | None = None):
        self.root = root or get_settings().audit_dir

    def path(self, lot_id):
        return self.root / (str(UUID(str(lot_id))) + ".jsonl")

    def read(self, lot_id):
        try:
            with self.path(lot_id).open(encoding="utf-8") as stream:
                fcntl.flock(stream, fcntl.LOCK_SH)
                return decode(stream, lot_id)
        except FileNotFoundError:
            return []
        except UnicodeError as error:
            raise JournalError("Journal com codificação inválida") from error

    def append(self, lot_id, sequence, last_hash):
        self.root.mkdir(parents=True, exist_ok=True)
        with self.path(lot_id).open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            records = decode(stream, lot_id)
            if records:
                latest = records[-1]
                if latest["sequence"] > sequence:
                    raise JournalError("Banco anterior ao checkpoint")
                if latest["sequence"] == sequence:
                    if latest["last_hash"] != last_hash:
                        raise JournalError("Hash diverge do checkpoint")
                    return False
            payload = {
                "lot_id": str(lot_id),
                "sequence": sequence,
                "last_hash": last_hash,
                "previous_checkpoint_hash": records[-1]["checkpoint_hash"]
                if records
                else ZERO_HASH,
                "created_at": datetime.now(UTC).isoformat(timespec="microseconds"),
                "key_version": KEY_VERSION,
            }
            digest = hashlib.sha256(canonical(payload)).hexdigest()
            value = {
                **payload,
                "checkpoint_hash": digest,
                "signature": sign({"kind": "checkpoint", "checkpoint_hash": digest}),
            }
            stream.write(canonical(value).decode() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return True
