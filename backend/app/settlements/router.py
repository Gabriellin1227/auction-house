from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth.dependencies import SessionDependency, require_role
from app.db.models import Bid, Lot, Receipt, Settlement, User
from app.lots.schemas import LotRead
from app.lots.service import LotService
from app.users.schemas import Role

router = APIRouter(tags=["Resultados e comprovantes"])


class ReceiptRead(BaseModel):
    id: UUID
    lot_id: UUID
    item_title: str
    image: str
    source_url: str
    item_attributes: dict
    winner_public_id: UUID
    amount_cents: int = Field(gt=0)
    currency: str
    settled_at: datetime


@router.get("/receipts/{receipt_id}", response_model=ReceiptRead)
def receipt(receipt_id: UUID, session: SessionDependency):
    value = session.get(Receipt, receipt_id)
    if value is None:
        raise HTTPException(404, "Comprovante não encontrado")
    return ReceiptRead(id=value.id, **value.snapshot)


class ParticipationRead(BaseModel):
    lot: LotRead
    highest_bid_cents: int
    leading: bool
    won: bool
    receipt_id: UUID | None


@router.get("/bidders/me/participations", response_model=list[ParticipationRead])
def participations(
    user: Annotated[User, Depends(require_role(Role.BIDDER))],
    session: SessionDependency,
    offset: int = Query(0, ge=0),
):
    lots = session.scalars(
        select(Lot)
        .where(
            select(Bid.id)
            .where(Bid.lot_id == Lot.id, Bid.bidder_id == user.id)
            .exists()
        )
        .order_by(Lot.created_at.desc(), Lot.id)
        .offset(offset)
        .limit(100)
    ).all()
    result = []
    for lot in lots:
        own = session.scalars(
            select(Bid)
            .where(Bid.lot_id == lot.id, Bid.bidder_id == user.id)
            .order_by(Bid.sequence.desc())
            .limit(1)
        ).one()
        winning = session.scalar(
            select(Receipt.id)
            .join(Settlement, Receipt.settlement_id == Settlement.id)
            .where(Settlement.lot_id == lot.id, Settlement.winning_bid_id == own.id)
        )
        result.append(
            ParticipationRead(
                lot=LotService(session).read(lot),
                highest_bid_cents=own.amount_cents,
                leading=lot.status not in {"closed", "cancelled"}
                and lot.current_bid_id == own.id,
                won=winning is not None,
                receipt_id=winning,
            )
        )
    return result
