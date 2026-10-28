import hashlib
import hmac
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.bids.schemas import BidAccepted, BidRead
from app.bids.signing import (
    KEY_VERSION,
    ZERO_HASH,
    canonical,
    head_record,
    record,
    sign,
)
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
from app.lots.service import LotService


class BidService:
    def __init__(self, session: Session):
        self.session = session

    def history(self, lot_id: UUID, after: int = 0):
        LotService(self.session).get(lot_id)
        return [
            BidRead(
                id=bid.id,
                bidder_public_id=public_id,
                sequence=bid.sequence,
                amount_cents=bid.amount_cents,
                accepted_at=bid.accepted_at,
            )
            for bid, public_id in self.session.execute(
                select(Bid, User.public_id)
                .join(User, User.id == Bid.bidder_id)
                .where(Bid.lot_id == lot_id, Bid.sequence > after)
                .order_by(Bid.sequence)
                .limit(100)
            )
        ]

    def place(self, lot_id: UUID, user_id: UUID, amount: int):
        # Retry only database-confirmed aborted transactions, never unknown commits.
        for attempt in range(3):
            try:
                result = self._place(lot_id, user_id, amount)
                self.session.commit()
                return result
            except OperationalError as error:
                self.session.rollback()
                if getattr(error.orig, "sqlstate", None) not in {"40P01", "40001"}:
                    raise
                if attempt == 2:
                    raise HTTPException(
                        409, "Disputa simultânea. Atualize o lote e tente novamente"
                    ) from None
            except Exception:
                self.session.rollback()
                raise

    def _place(self, lot_id: UUID, user_id: UUID, amount: int):
        lot = self.session.scalar(
            select(Lot)
            .where(Lot.id == lot_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if lot is None:
            raise HTTPException(404, "Lote não encontrado")
        user = self.session.scalar(
            select(User)
            .where(User.id == user_id)
            .execution_options(populate_existing=True)
        )
        if user is None or not user.active:
            raise HTTPException(401, "Conta indisponível")
        if user.role != "bidder" or lot.seller_id == user_id:
            raise HTTPException(403, "Leiloeiro não pode dar lances")
        previous = (
            self.session.get(Bid, lot.current_bid_id) if lot.current_bid_id else None
        )
        owners = {user_id}
        if previous:
            owners.add(previous.bidder_id)
        # Global order: lot, then all involved wallets ordered by their IDs.
        wallets = {
            wallet.user_id: wallet
            for wallet in self.session.scalars(
                select(Wallet)
                .where(Wallet.user_id.in_(owners))
                .order_by(Wallet.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        now = self.session.scalar(select(func.clock_timestamp()))
        if lot.status in {"closed", "cancelled"} or now >= lot.ends_at:
            raise HTTPException(409, "Lote encerrado ou cancelado")
        if now < lot.starts_at:
            raise HTTPException(409, "Lote ainda não iniciado")
        if previous and previous.bidder_id == user_id:
            raise HTTPException(409, "Você já está ganhando este lote")
        minimum = (
            previous.amount_cents + lot.min_increment_cents
            if previous
            else lot.opening_bid_cents
        )
        if amount < minimum:
            raise HTTPException(409, f"Lance abaixo do mínimo de {minimum} centavos")
        wallet = wallets.get(user_id)
        if wallet is None or len(wallets) != len(owners):
            raise HTTPException(409, "Carteira indisponível")
        if amount > wallet.available_cents:
            raise HTTPException(409, "Saldo disponível insuficiente")

        head = self.session.get(AuditHead, lot_id)
        if head is None:
            if self.session.scalar(
                select(func.count()).select_from(Bid).where(Bid.lot_id == lot_id)
            ):
                raise HTTPException(409, "Histórico de lances inconsistente")
            head = AuditHead(
                lot_id=lot_id,
                last_sequence=0,
                last_hash=ZERO_HASH,
                key_version=KEY_VERSION,
                signature=sign(head_record(lot_id, 0, ZERO_HASH)),
            )
            self.session.add(head)
        expected_sequence = previous.sequence if previous else 0
        expected_hash = previous.record_hash if previous else ZERO_HASH
        if (
            head.key_version != KEY_VERSION
            or head.last_sequence != expected_sequence
            or head.last_hash != expected_hash
            or not hmac.compare_digest(
                head.signature,
                sign(head_record(lot_id, head.last_sequence, head.last_hash)),
            )
        ):
            raise HTTPException(409, "Histórico de lances inconsistente")

        if previous:
            reservation = self.session.scalar(
                select(WalletReservation).where(
                    WalletReservation.lot_id == lot_id,
                    WalletReservation.status == "active",
                )
            )
            old_wallet = wallets[previous.bidder_id]
            if (
                reservation is None
                or reservation.bid_id != previous.id
                or reservation.wallet_id != old_wallet.id
                or reservation.amount_cents != previous.amount_cents
            ):
                raise HTTPException(409, "Reserva anterior inconsistente")
            old_wallet.reserved_cents -= reservation.amount_cents
            reservation.status = "released"
            reservation.released_at = now
            self.session.add(
                self.entry(old_wallet, previous, "release", reservation.amount_cents)
            )
            # Free the partial unique index before inserting the next active reserve.
            self.session.flush()

        bid = Bid(
            id=uuid4(),
            lot_id=lot_id,
            bidder_id=user_id,
            sequence=expected_sequence + 1,
            amount_cents=amount,
            accepted_at=now,
            previous_hash=head.last_hash,
            key_version=KEY_VERSION,
        )
        bid.record_hash = hashlib.sha256(
            canonical(record(bid, user.public_id))
        ).hexdigest()
        bid.signature = sign({"kind": "bid", "record_hash": bid.record_hash})
        self.session.add(bid)
        self.session.flush()
        wallet.reserved_cents += amount
        self.session.add(
            WalletReservation(
                lot_id=lot_id,
                wallet_id=wallet.id,
                bid_id=bid.id,
                amount_cents=amount,
            )
        )
        self.session.add(self.entry(wallet, bid, "reserve", amount))
        lot.current_bid_id = bid.id
        lot.status = "live"
        lot.version += 1
        extended = lot.ends_at - now <= timedelta(seconds=120)
        if extended:
            lot.ends_at = now + timedelta(seconds=120)
        head.last_sequence = bid.sequence
        head.last_hash = bid.record_hash
        head.signature = sign(head_record(lot_id, bid.sequence, bid.record_hash))
        result = BidAccepted(
            id=bid.id,
            bidder_public_id=user.public_id,
            sequence=bid.sequence,
            amount_cents=amount,
            accepted_at=now,
            lot_id=lot_id,
            version=lot.version,
            ends_at=lot.ends_at,
            extended=extended,
        )
        payload = result.model_dump(mode="json")
        for event_type in ["BidAccepted"] + (["AuctionExtended"] if extended else []):
            self.session.add(
                OutboxEvent(
                    lot_id=lot_id,
                    aggregate_version=lot.version,
                    event_type=event_type,
                    payload=payload,
                )
            )
        self.session.flush()
        return result

    @staticmethod
    def entry(wallet, bid, kind, amount):
        return WalletEntry(
            wallet_id=wallet.id,
            lot_id=bid.lot_id,
            bid_id=bid.id,
            type=kind,
            amount_cents=amount,
            operation_key=f"{kind}:{bid.id}",
        )
