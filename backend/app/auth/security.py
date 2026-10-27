from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import get_settings

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummy-password-for-timing-only")


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Credenciais inválidas ou sessão expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )


def signing_key() -> str:
    secret = get_settings().auth_secret
    if secret is None:
        raise HTTPException(status_code=503, detail="Autenticação não configurada")
    return secret.get_secret_value()


def create_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": "auction-house",
            "aud": "auction-house-api",
        },
        signing_key(),
        algorithm="HS256",
    )


def decode_token(token: str) -> UUID:
    key = signing_key()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            issuer="auction-house",
            audience="auction-house-api",
            options={"require": ["sub", "iat", "exp", "iss", "aud"]},
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, ValueError, TypeError, AttributeError):
        raise unauthorized() from None
