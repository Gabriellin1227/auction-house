from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import SessionDependency, require_role
from app.bids.schemas import BidAccepted, BidCreate, BidRead
from app.bids.service import BidService
from app.db.models import User
from app.users.schemas import Role

router = APIRouter(prefix="/lots", tags=["Lances"])


@router.get("/{lot_id}/bids", response_model=list[BidRead])
def history(lot_id: UUID, session: SessionDependency, after: int = Query(0, ge=0)):
    return BidService(session).history(lot_id, after)


@router.post("/{lot_id}/bids", response_model=BidAccepted, status_code=201)
def place_bid(
    lot_id: UUID,
    data: BidCreate,
    user: Annotated[User, Depends(require_role(Role.BIDDER))],
    session: SessionDependency,
):
    return BidService(session).place(lot_id, user.id, data.amount_cents)
