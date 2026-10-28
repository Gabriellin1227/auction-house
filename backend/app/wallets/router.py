from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import CurrentUser, SessionDependency, require_role
from app.db.models import User
from app.users.schemas import Role
from app.wallets.service import WalletService

router = APIRouter(prefix="/wallets", tags=["Carteira"])


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    balance_cents: int
    reserved_cents: int
    available_cents: int
    currency: str = "BRL"


@router.get("/me", response_model=WalletRead)
def read_wallet(user: CurrentUser, session: SessionDependency):
    return WalletService(session).get(user.id)


class DepositCreate(BaseModel):
    amount_cents: int = Field(gt=0, le=100_000_000, strict=True)


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: str
    amount_cents: int
    created_at: datetime


@router.get("/me/entries", response_model=list[EntryRead])
def entries(user: CurrentUser, session: SessionDependency):
    return WalletService(session).entries(user.id)


@router.post("/me/deposits", response_model=WalletRead)
def deposit(
    data: DepositCreate,
    user: Annotated[User, Depends(require_role(Role.BIDDER))],
    session: SessionDependency,
    idempotency_key: Annotated[UUID, Header()],
):
    return WalletService(session).deposit(user.id, data.amount_cents, idempotency_key)
