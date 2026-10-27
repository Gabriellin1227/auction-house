from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth.dependencies import SessionDependency
from app.auth.security import DUMMY_HASH, create_token, password_hash, unauthorized
from app.users.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenRead)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDependency
):
    if not 1 <= len(form.password) <= 128 or len(form.username) > 320:
        raise unauthorized()
    user = UserRepository(session).by_email(form.username.strip().lower())
    valid = password_hash.verify(
        form.password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid or not user.active:
        raise unauthorized()
    return TokenRead(access_token=create_token(user.id))
