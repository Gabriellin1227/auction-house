import hashlib
import hmac
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.journal import Journal, JournalError
from app.bids.signing import (
    KEY_VERSION,
    ZERO_HASH,
    canonical,
    head_record,
    record,
    sign,
)
from app.db.models import AuditHead, Bid, Lot, User


class AuditService:
    def __init__(self, session: Session):
        self.session = session

    def verify(self, lot_id: UUID, *, after=0):
        # Read the journal BEFORE the DB snapshot: a newer concurrent checkpoint
        # must not be compared against an older PostgreSQL snapshot.
        checkpoint_issues = []
        storage_unavailable = False
        try:
            checkpoints = Journal().read(lot_id)
        except JournalError:
            checkpoints = []
            checkpoint_issues.append("Checkpoint inválido ou journal incompleto")
        except OSError:
            storage_unavailable = True
            checkpoints = []
            checkpoint_issues.append("Armazenamento de checkpoints indisponível")
        lot = self.session.get(Lot, lot_id)
        if lot is None:
            raise HTTPException(404, "Lote não encontrado")
        head = self.session.get(AuditHead, lot_id)
        rows = self.session.execute(
            select(Bid, User.public_id)
            .join(User, User.id == Bid.bidder_id)
            .where(Bid.lot_id == lot_id)
            .order_by(Bid.sequence)
        ).all()
        issues, hashes, history = [], {0: ZERO_HASH}, []
        previous = ZERO_HASH
        for sequence, (bid, public_id) in enumerate(rows, start=1):
            digest = hashlib.sha256(canonical(record(bid, public_id))).hexdigest()
            if (
                bid.sequence != sequence
                or bid.previous_hash != previous
                or bid.key_version != KEY_VERSION
                or not hmac.compare_digest(bid.record_hash, digest)
                or not hmac.compare_digest(
                    bid.signature, sign({"kind": "bid", "record_hash": digest})
                )
            ):
                issues.append("Sequência, hash ou assinatura de lance inconsistente")
            hashes[bid.sequence] = digest
            previous = digest
            if bid.sequence > after and len(history) < 100:
                history.append(
                    {
                        "id": str(bid.id),
                        "bidder_public_id": str(public_id),
                        "sequence": bid.sequence,
                        "amount_cents": bid.amount_cents,
                        "accepted_at": bid.accepted_at.isoformat(),
                        "previous_hash": bid.previous_hash,
                        "record_hash": bid.record_hash,
                        "signature": bid.signature,
                        "key_version": bid.key_version,
                    }
                )
        if head is None:
            issues.append("Cabeçalho autenticado ausente")
        elif (
            head.last_sequence != len(rows)
            or head.last_hash != previous
            or head.key_version != KEY_VERSION
            or not hmac.compare_digest(
                head.signature,
                sign(head_record(lot_id, head.last_sequence, head.last_hash)),
            )
        ):
            issues.append("Cabeçalho não corresponde ao histórico")
        current = rows[-1][0].id if rows else None
        if lot.current_bid_id != current:
            issues.append("Liderança não corresponde ao último lance")
        for checkpoint in checkpoints:
            if hashes.get(checkpoint["sequence"]) != checkpoint["last_hash"]:
                issues.append(
                    "Histórico diverge de checkpoint externo: "
                    "possível remoção ou rollback"
                )
        checkpoint_sequence = checkpoints[-1]["sequence"] if checkpoints else None
        state = (
            "invalid"
            if checkpoint_issues
            else ("anchored" if checkpoint_sequence == len(rows) else "pending")
        )
        if storage_unavailable:
            state = "unavailable"
        if issues:
            state = "invalid" if checkpoints or checkpoint_issues else state
        return {
            "lot_id": str(lot_id),
            "integrity": "invalid"
            if issues or (checkpoint_issues and not storage_unavailable)
            else "unavailable"
            if storage_unavailable
            else "valid",
            "checkpoint_status": state,
            "verified_count": len(rows),
            "checkpoint_sequence": checkpoint_sequence,
            "head_sequence": head.last_sequence if head else None,
            "last_hash": previous,
            "issues": list(dict.fromkeys(issues + checkpoint_issues)),
            "history": history,
            "next_after": history[-1]["sequence"]
            if history
            and any(bid.sequence > history[-1]["sequence"] for bid, _ in rows)
            else None,
        }
