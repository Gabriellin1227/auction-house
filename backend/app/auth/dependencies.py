from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token, unauthorized
from app.db.models import User
from app.db.session import get_session
from app.users.repository import UserRepository
from app.users.schemas import Role

SessionDependency = Annotated[Session, Depends(get_session)]
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/token")


def current_user(
    session: SessionDependency, token: Annotated[str, Depends(oauth2)]
) -> User:
    user = UserRepository(session).by_id(decode_token(token))
    if user is None or not user.active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(role: Role):
    def check(user: CurrentUser) -> User:
        if user.role != role.value:
            raise HTTPException(403, "Seu papel não permite esta operação")
        return user

    return check
