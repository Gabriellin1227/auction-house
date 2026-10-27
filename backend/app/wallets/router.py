from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, SessionDependency
from app.db.models import Wallet

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
    wallet = session.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if wallet is None:
        raise HTTPException(409, "Carteira indisponível")
    return wallet
