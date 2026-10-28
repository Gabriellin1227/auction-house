"""Explicit, idempotent demo users. Never resets passwords or balances."""

import argparse
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.auth.security import password_hash
from app.config import get_settings
from app.db.models import Lot, User, Wallet
from app.db.session import get_engine
from app.lots.schemas import LotCreate
from app.lots.service import LotService

DEMO_PASSWORD = "DemoAuction2026!"
DEMO_USERS = (
    ("Leiloeiro Demo", "leiloeiro@example.com", "auctioneer"),
    ("Cliente Um", "cliente1@example.com", "bidder"),
    ("Cliente Dois", "cliente2@example.com", "bidder"),
)


def seed_users(session: Session) -> int:
    created = 0
    for name, email, role in DEMO_USERS:
        user_id = session.scalar(
            insert(User)
            .values(
                name=name,
                email=email,
                role=role,
                password_hash=password_hash.hash(DEMO_PASSWORD),
            )
            .on_conflict_do_nothing(index_elements=[User.email])
            .returning(User.id)
        )
        if user_id is not None:
            session.add(Wallet(user_id=user_id))
            created += 1
    session.flush()
    return created


def seed_open_lot(session: Session) -> tuple[str, bool]:
    """Serialize seed runs; reuse a persisted, open demo lot or import a real one."""
    session.execute(text("SELECT pg_advisory_xact_lock(20261028, 1)"))
    seller = session.scalar(select(User).where(User.email == DEMO_USERS[0][1]))
    if seller is None or not seller.active or seller.role != "auctioneer":
        raise HTTPException(
            409, "Leiloeiro demo ausente, inativo ou com papel diferente"
        )
    now = session.scalar(select(func.clock_timestamp()))
    candidates = session.scalars(
        select(Lot)
        .where(
            Lot.seller_id == seller.id,
            Lot.source_provider == "cleveland",
            Lot.status.not_in(["closed", "cancelled"]),
            Lot.starts_at <= now,
            Lot.ends_at > now + timedelta(minutes=5),
        )
        .order_by(Lot.ends_at.desc())
    )
    for lot in candidates:
        if (get_settings().media_dir / lot.local_image_key).is_file():
            result = AuditService(session).verify(lot.id)
            if result["integrity"] != "valid":
                raise HTTPException(409, "Auditoria do lote demo exige revisão")
            session.commit()
            return str(lot.id), False
    # LotService commits the image snapshot, lot and signed initial head together.
    # The advisory transaction lock remains held until that commit completes.
    lot = LotService(session).create(
        seller.id,
        LotCreate(
            external_item_id=94979,
            category="fine-art",
            opening_bid_cents=1000,
            min_increment_cents=100,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(hours=24),
        ),
    )
    return lot.id, True


def main():
    parser = argparse.ArgumentParser(
        description="Criar usuários e lote de demonstração"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        required=True,
        help="Confirma criação de contas com senha pública de demo",
    )
    parser.parse_args()
    with Session(get_engine()) as session:
        with session.begin():
            created = seed_users(session)
        print(f"Seed de contas: {created} criadas; existentes preservadas.")
        try:
            lot_id, imported = seed_open_lot(session)
        except HTTPException as error:
            session.rollback()
            parser.exit(1, f"Não foi possível preparar o lote demo: {error.detail}\n")
        print(f"Lote aberto {'criado' if imported else 'reutilizado'}: {lot_id}")


if __name__ == "__main__":
    main()
