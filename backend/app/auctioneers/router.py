from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth.dependencies import SessionDependency, require_role
from app.db.models import Lot, Settlement, User
from app.users.schemas import Role

router = APIRouter(prefix="/auctioneers", tags=["Leiloeiro"])


class AuctioneerSummary(BaseModel):
    total_lots: int
    total_received_cents: int


@router.get("/me/summary", response_model=AuctioneerSummary)
def summary(
    session: SessionDependency,
    user: Annotated[User, Depends(require_role(Role.AUCTIONEER))],
):
    total_lots = session.scalar(
        select(func.count()).select_from(Lot).where(Lot.seller_id == user.id)
    )
    received = session.scalar(
        select(func.coalesce(func.sum(Settlement.amount_cents), 0))
        .join(Lot, Settlement.lot_id == Lot.id)
        .where(Lot.seller_id == user.id)
    )
    return AuctioneerSummary(total_lots=total_lots, total_received_cents=received)
