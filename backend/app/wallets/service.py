import hashlib
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Wallet, WalletEntry


class WalletService:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: UUID, *, lock: bool = False):
        query = select(Wallet).where(Wallet.user_id == user_id)
        wallet = self.session.scalar(query.with_for_update() if lock else query)
        if wallet is None:
            raise HTTPException(409, "Carteira indisponível")
        return wallet

    def entries(self, user_id: UUID):
        wallet = self.get(user_id)
        return self.session.scalars(
            select(WalletEntry)
            .where(WalletEntry.wallet_id == wallet.id)
            .order_by(WalletEntry.created_at.desc())
            .limit(100)
        ).all()

    def deposit(self, user_id: UUID, amount: int, request_id: UUID):
        wallet = self.get(user_id, lock=True)
        key = f"deposit:{user_id}:{request_id}"
        digest = hashlib.sha256(str(amount).encode()).hexdigest()
        previous = self.session.scalar(
            select(WalletEntry).where(WalletEntry.operation_key == key)
        )
        if previous:
            if previous.request_hash != digest:
                raise HTTPException(409, "Chave já utilizada para outro valor")
            return wallet
        wallet.balance_cents += amount
        self.session.add(
            WalletEntry(
                wallet_id=wallet.id,
                type="deposit",
                amount_cents=amount,
                operation_key=key,
                request_hash=digest,
            )
        )
        self.session.commit()
        self.session.refresh(wallet)
        return wallet
