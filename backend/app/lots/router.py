from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select

from app.auth.dependencies import SessionDependency, require_role
from app.catalog.service import CATEGORIES, CatalogService
from app.db.models import Lot, User
from app.lots.schemas import LotCreate, LotRead, LotUpdate
from app.lots.service import LotService
from app.users.schemas import Role

router = APIRouter(tags=["Lotes e catálogo"])
Seller = Annotated[User, Depends(require_role(Role.AUCTIONEER))]


@router.get("/categories")
def categories():
    return CATEGORIES


@router.get("/catalog/items")
def catalog_items(user: Seller, q: str = Query(default="", max_length=120)):
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "image": item.get("images", {}).get("web", {}).get("url", ""),
        }
        for item in CatalogService().search(q)
        if item.get("share_license_status") == "CC0"
    ]


@router.get("/lots", response_model=list[LotRead])
def list_lots(
    session: SessionDependency,
    q: str = Query(default="", max_length=120),
    category: str = "",
    sort: str = "ending",
    status: str = "",
):
    service = LotService(session)
    query = select(Lot).where(Lot.status != "cancelled")
    if q:
        query = query.where(Lot.item_title.icontains(q, autoescape=True))
    if category:
        service.category(category)
        query = query.where(Lot.item_attributes["category"].astext == category)
    lots = [
        service.read(lot)
        for lot in session.scalars(query.order_by(Lot.ends_at).limit(100))
    ]
    if status:
        lots = [lot for lot in lots if lot.status == status]
    if sort == "price":
        lots.sort(key=lambda item: item.currentBid, reverse=True)
    return lots


@router.get("/lots/mine", response_model=list[LotRead])
def own_lots(user: Seller, session: SessionDependency):
    return [
        LotService(session).read(lot)
        for lot in session.scalars(
            select(Lot).where(Lot.seller_id == user.id).order_by(Lot.created_at.desc())
        )
    ]


@router.post("/lots", response_model=LotRead, status_code=201)
def create_lot(data: LotCreate, user: Seller, session: SessionDependency):
    return LotService(session).create(user.id, data)


@router.get("/lots/{lot_id}", response_model=LotRead)
def read_lot(lot_id: UUID, session: SessionDependency):
    service = LotService(session)
    return service.read(service.get(lot_id))


@router.patch("/lots/{lot_id}", response_model=LotRead)
def update_lot(lot_id: UUID, data: LotUpdate, user: Seller, session: SessionDependency):
    return LotService(session).update(lot_id, user.id, data)


@router.delete("/lots/{lot_id}", status_code=204)
def cancel_lot(lot_id: UUID, user: Seller, session: SessionDependency):
    LotService(session).cancel(lot_id, user.id)
    return Response(status_code=204)


@router.get("/stats")
def stats(session: SessionDependency):
    lots = [
        LotService(session).read(lot)
        for lot in session.scalars(select(Lot).where(Lot.status != "cancelled"))
    ]
    live = [lot for lot in lots if lot.status == "live"]
    return {
        "openLots": len(live),
        "valueOnFloor": sum(lot.currentBid for lot in live),
        "bidsPlaced": sum(lot.bids for lot in lots),
        "hoursOpen": 24,
    }
