from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().sqlalchemy_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=240,
        connect_args={"connect_timeout": 5},
    )


def get_session() -> Iterator[Session]:
    # Services explicitly commit/rollback their transaction; no implicit commits.
    with Session(get_engine()) as session:
        yield session
