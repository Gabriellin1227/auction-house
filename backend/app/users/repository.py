from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, Wallet


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def by_id(self, user_id: UUID, *, lock: bool = False) -> User | None:
        query = select(User).where(User.id == user_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def add_with_wallet(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        self.session.add(Wallet(user_id=user.id))
        self.session.flush()
        return user
