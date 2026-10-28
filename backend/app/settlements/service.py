import hashlib
import hmac
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.bids.signing import KEY_VERSION, canonical, head_record, record, sign
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


class SettlementService:
    def __init__(self, session: Session):
        self.session = session

    def close(self, lot_id: UUID) -> bool:
        try:
            # Do not leave a worker indefinitely waiting for a busy wallet.
            self.session.execute(text("SET LOCAL lock_timeout = '5s'"))
            lot = self.session.scalar(
                select(Lot)
                .where(Lot.id == lot_id)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if lot is None or lot.status in {"closed", "cancelled"}:
                self.session.rollback()
                return False
            now = self.session.scalar(select(func.clock_timestamp()))
            if now < lot.ends_at:
                self.session.rollback()
                return False
            verification = AuditService(self.session).verify(lot_id)
            if (
                verification["integrity"] != "valid"
                or verification["checkpoint_status"] == "invalid"
            ):
                raise HTTPException(
                    409, "Auditoria inconsistente; fechamento bloqueado"
                )
            receipt_id = None
            if lot.current_bid_id:
                receipt_id = self._settle(lot)
            elif self.session.scalar(
                select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id)
            ):
                raise HTTPException(409, "Lote com histórico e sem liderança")
            now = self.session.scalar(select(func.clock_timestamp()))
            lot.status = "closed"
            lot.closed_at = now
            lot.version += 1
            self.session.add(
                OutboxEvent(
                    lot_id=lot.id,
                    aggregate_version=lot.version,
                    event_type="AuctionClosed",
                    payload={
                        "lot_id": str(lot.id),
                        "closed_at": now.isoformat(),
                        "receipt_id": str(receipt_id) if receipt_id else None,
                        "sold": receipt_id is not None,
                    },
                )
            )
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def _settle(self, lot):
        bid = self.session.get(Bid, lot.current_bid_id)
        buyer = self.session.get(User, bid.bidder_id)
        head = self.session.get(AuditHead, lot.id)
        digest = hashlib.sha256(canonical(record(bid, buyer.public_id))).hexdigest()
        if (
            head is None
            or head.key_version != KEY_VERSION
            or bid.key_version != KEY_VERSION
            or head.last_sequence != bid.sequence
            or head.last_hash != digest
            or not hmac.compare_digest(bid.record_hash, digest)
            or not hmac.compare_digest(
                bid.signature, sign({"kind": "bid", "record_hash": digest})
            )
            or not hmac.compare_digest(
                head.signature, sign(head_record(lot.id, bid.sequence, digest))
            )
        ):
            raise HTTPException(409, "Lance vencedor inconsistente")
        wallets = {
            wallet.user_id: wallet
            for wallet in self.session.scalars(
                select(Wallet)
                .where(Wallet.user_id.in_([buyer.id, lot.seller_id]))
                .order_by(Wallet.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        if len(wallets) != 2:
            raise HTTPException(409, "Carteiras de liquidação indisponíveis")
        buyer_wallet, seller_wallet = wallets[buyer.id], wallets[lot.seller_id]
        reservation = self.session.scalar(
            select(WalletReservation).where(
                WalletReservation.lot_id == lot.id,
                WalletReservation.status == "active",
            )
        )
        if (
            reservation is None
            or reservation.bid_id != bid.id
            or reservation.wallet_id != buyer_wallet.id
            or reservation.amount_cents != bid.amount_cents
            or buyer_wallet.reserved_cents < bid.amount_cents
            or buyer_wallet.balance_cents < bid.amount_cents
        ):
            raise HTTPException(409, "Reserva de liquidação inconsistente")
        now = self.session.scalar(select(func.clock_timestamp()))
        reservation.status = "captured"
        reservation.released_at = now
        buyer_wallet.reserved_cents -= bid.amount_cents
        buyer_wallet.balance_cents -= bid.amount_cents
        seller_wallet.balance_cents += bid.amount_cents
        settlement = Settlement(
            id=uuid4(),
            lot_id=lot.id,
            winning_bid_id=bid.id,
            buyer_wallet_id=buyer_wallet.id,
            seller_wallet_id=seller_wallet.id,
            amount_cents=bid.amount_cents,
            settled_at=now,
        )
        self.session.add(settlement)
        self.session.flush()
        receipt = Receipt(
            id=uuid4(),
            settlement_id=settlement.id,
            snapshot={
                "lot_id": str(lot.id),
                "item_title": lot.item_title,
                "image": "/api/media/" + lot.local_image_key,
                "source_url": lot.source_url,
                "item_attributes": lot.item_attributes,
                "winner_public_id": str(buyer.public_id),
                "amount_cents": bid.amount_cents,
                "currency": "BRL",
                "settled_at": now.isoformat(),
            },
        )
        self.session.add(receipt)
        for wallet, kind in [(buyer_wallet, "debit"), (seller_wallet, "credit")]:
            self.session.add(
                WalletEntry(
                    wallet_id=wallet.id,
                    lot_id=lot.id,
                    bid_id=bid.id,
                    type=kind,
                    amount_cents=bid.amount_cents,
                    operation_key=f"settlement:{lot.id}:{kind}",
                )
            )
        return receipt.id
