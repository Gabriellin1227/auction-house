from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.bids.signing import ZERO_HASH, head_record, sign
from app.catalog.service import CATEGORIES, CatalogService
from app.config import get_settings
from app.db.models import AuditHead, Bid, Lot, Receipt, Settlement, User
from app.lots.schemas import LotCreate, LotRead, LotUpdate


class LotService:
    def __init__(self, session: Session):
        self.session = session

    def now(self):
        return self.session.scalar(select(func.clock_timestamp()))

    def category(self, slug):
        value = next((c for c in CATEGORIES if c["slug"] == slug), None)
        if value is None:
            raise HTTPException(422, "Categoria inválida")
        return value

    def get(self, lot_id: UUID, *, owner=None, lock=False):
        query = select(Lot).where(Lot.id == lot_id)
        if lock:
            query = query.with_for_update()
        lot = self.session.scalar(query)
        if lot is None or (owner is None and lot.status == "cancelled"):
            raise HTTPException(404, "Lote não encontrado")
        if owner is not None and lot.seller_id != owner:
            raise HTTPException(403, "Este lote pertence a outro leiloeiro")
        return lot

    def read(self, lot: Lot):
        count = self.session.scalar(
            select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id)
        )
        bid = self.session.get(Bid, lot.current_bid_id) if lot.current_bid_id else None
        settlement = self.session.scalar(
            select(Settlement).where(Settlement.lot_id == lot.id)
        )
        receipt_id = (
            self.session.scalar(
                select(Receipt.id).where(Receipt.settlement_id == settlement.id)
            )
            if settlement
            else None
        )
        category = self.category(lot.item_attributes.get("category", "fine-art"))
        now = self.now()
        status = lot.status
        if status not in {"closed", "cancelled"}:
            status = (
                "closed"
                if now >= lot.ends_at
                else "scheduled"
                if now < lot.starts_at
                else "live"
            )
        return LotRead(
            id=str(lot.id),
            number=str(lot.id)[:8].upper(),
            title=lot.item_title,
            category=category["slug"],
            categoryName=category["name"],
            image="/api/media/" + lot.local_image_key,
            currentBid=bid.amount_cents if bid else lot.opening_bid_cents,
            bids=count,
            endsAt=int(lot.ends_at.timestamp() * 1000),
            startsAt=int(lot.starts_at.timestamp() * 1000),
            status=status,
            increment=lot.min_increment_cents,
            sourceUrl=lot.source_url,
            attributes=lot.item_attributes,
            leaderPublicId=str(self.session.get(User, bid.bidder_id).public_id)
            if bid
            else None,
            version=lot.version,
            closureComplete=lot.status == "closed",
            sold=settlement is not None,
            settledAmount=settlement.amount_cents if settlement else None,
            receiptId=str(receipt_id) if receipt_id else None,
        )

    def create(self, owner: UUID, data: LotCreate):
        self.category(data.category)
        if data.starts_at >= data.ends_at or data.ends_at <= self.now():
            raise HTTPException(
                422, "Período inválido: o fim deve ser futuro e posterior ao início"
            )
        catalog = CatalogService()
        item = catalog.item(data.external_item_id)
        key = catalog.save_image(item)
        try:
            lot = Lot(
                seller_id=owner,
                source_provider="cleveland",
                external_item_id=str(item["id"]),
                source_url=item["url"],
                item_title=item["title"],
                local_image_key=key,
                item_attributes={
                    "category": data.category,
                    "technique": item.get("technique"),
                    "date": item.get("creation_date"),
                    "license": "CC0",
                },
                opening_bid_cents=data.opening_bid_cents,
                min_increment_cents=data.min_increment_cents,
                starts_at=data.starts_at,
                original_ends_at=data.ends_at,
                ends_at=data.ends_at,
            )
            self.session.add(lot)
            self.session.flush()
            self.session.add(
                AuditHead(
                    lot_id=lot.id,
                    last_sequence=0,
                    last_hash=ZERO_HASH,
                    key_version=1,
                    signature=sign(head_record(lot.id, 0, ZERO_HASH)),
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            (get_settings().media_dir / key).unlink(missing_ok=True)
            raise
        self.session.refresh(lot)
        return self.read(lot)

    def update(self, lot_id: UUID, owner: UUID, data: LotUpdate):
        lot = self.get(lot_id, owner=owner, lock=True)
        if lot.status in {"cancelled", "closed"} or self.now() >= lot.starts_at:
            raise HTTPException(
                409, "Só é possível editar lotes agendados, antes do início"
            )
        if self.session.scalar(
            select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id)
        ):
            raise HTTPException(409, "Lote com lances não pode ser editado")
        now = self.now()
        changes = data.model_dump(exclude_unset=True)
        if any(value is None for value in changes.values()):
            raise HTTPException(422, "Campos não podem ser nulos")
        if "category" in changes:
            self.category(changes.pop("category"))
            lot.item_attributes = {**lot.item_attributes, "category": data.category}
        for key, value in changes.items():
            setattr(lot, key, value)
        if lot.starts_at >= lot.ends_at or lot.starts_at <= now:
            raise HTTPException(422, "Período inválido para edição")
        lot.original_ends_at = lot.ends_at
        lot.version += 1
        self.session.commit()
        self.session.refresh(lot)
        return self.read(lot)

    def cancel(self, lot_id: UUID, owner: UUID):
        lot = self.get(lot_id, owner=owner, lock=True)
        if lot.status in {"closed", "cancelled"} or self.now() >= lot.ends_at:
            raise HTTPException(409, "Lote já encerrado ou cancelado")
        if lot.current_bid_id or self.session.scalar(
            select(func.count()).select_from(Bid).where(Bid.lot_id == lot.id)
        ):
            raise HTTPException(409, "Não é possível cancelar lote com lances")
        lot.status = "cancelled"
        lot.version += 1
        self.session.commit()
