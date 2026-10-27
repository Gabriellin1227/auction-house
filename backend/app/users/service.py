from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import password_hash
from app.db.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = UserRepository(session)

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            if error.orig.diag.constraint_name == "uq_users_email":
                raise HTTPException(409, "E-mail já cadastrado") from None
            raise

    def create(self, data: UserCreate) -> User:
        user = User(
            name=data.name,
            email=str(data.email),
            role=data.role.value,
            password_hash=password_hash.hash(data.password.get_secret_value()),
        )
        try:
            self.repository.add_with_wallet(user)
            self.commit()
        except IntegrityError as error:
            self.session.rollback()
            if error.orig.diag.constraint_name == "uq_users_email":
                raise HTTPException(409, "E-mail já cadastrado") from None
            raise
        self.session.refresh(user)
        return user

    def active_for_update(self, user_id: UUID) -> User:
        user = self.repository.by_id(user_id, lock=True)
        if user is None or not user.active:
            raise HTTPException(401, "Conta indisponível")
        return user

    def update(self, user_id: UUID, data: UserUpdate) -> User:
        user = self.active_for_update(user_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, str(value))
        self.commit()
        self.session.refresh(user)
        return user

    def deactivate(self, user_id: UUID) -> None:
        user = self.active_for_update(user_id)
        user.active = False
        self.commit()
