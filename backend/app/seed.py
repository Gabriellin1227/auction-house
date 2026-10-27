"""Explicit, idempotent demo users. Never resets passwords or balances."""

import argparse

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.security import password_hash
from app.db.models import User, Wallet
from app.db.session import get_engine

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


def main():
    parser = argparse.ArgumentParser(description="Criar usuários de demonstração")
    parser.add_argument(
        "--demo",
        action="store_true",
        required=True,
        help="Confirma criação de contas com senha pública de demo",
    )
    parser.parse_args()
    with Session(get_engine()) as session, session.begin():
        created = seed_users(session)
    print(f"Seed concluído: {created} usuários criados; existentes preservados.")


if __name__ == "__main__":
    main()
