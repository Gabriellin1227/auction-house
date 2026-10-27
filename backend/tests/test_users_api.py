from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import password_hash
from app.config import get_settings
from app.db.models import Lot, User, Wallet
from app.seed import DEMO_PASSWORD, seed_users

PASSWORD = "TestPassword2026!"


def register(client, email="user@example.com", role="bidder"):
    return client.post(
        "/users",
        json={
            "name": "  Usuário Teste  ",
            "email": email,
            "password": PASSWORD,
            "role": role,
        },
    )


def login(client, email="user@example.com", password=PASSWORD):
    response = client.post(
        "/auth/token", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_account_crud_wallet_and_immediate_deactivation(client, database):
    response = register(client, " User@Example.COM ")
    assert response.status_code == 201
    user = response.json()
    assert user["name"] == "Usuário Teste"
    assert user["email"] == "user@example.com"
    assert user["role"] == "bidder"
    assert "password" not in response.text
    assert "password_hash" not in user
    with Session(database) as session:
        stored = session.get(User, user["id"])
        assert stored.password_hash != PASSWORD
        assert stored.password_hash.startswith("$argon2")
        assert password_hash.verify(PASSWORD, stored.password_hash)
    headers = login(client)
    assert client.get("/users/me", headers=headers).json()["id"] == user["id"]
    wallet = client.get("/wallets/me", headers=headers)
    assert wallet.status_code == 200
    assert wallet.json()["balance_cents"] == 0
    assert wallet.json()["reserved_cents"] == 0
    assert wallet.json()["available_cents"] == 0
    assert wallet.json()["currency"] == "BRL"
    updated = client.patch(
        "/users/me",
        headers=headers,
        json={"name": "Novo nome", "email": " UPDATED@EXAMPLE.COM "},
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated@example.com"
    assert updated.json()["name"] == "Novo nome"
    assert (
        client.post(
            "/auth/token", data={"username": "user@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )
    headers = login(client, "updated@example.com")
    deleted = client.delete("/users/me", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/users/me", headers=headers).status_code == 401
    assert client.get("/wallets/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/auth/token",
            data={"username": "updated@example.com", "password": PASSWORD},
        ).status_code
        == 401
    )
    with Session(database) as session:
        assert session.get(User, user["id"]).active is False
        assert session.get(Wallet, wallet.json()["id"]) is not None


def test_duplicate_registration_is_atomic(client, database):
    assert register(client).status_code == 201
    assert register(client, "USER@EXAMPLE.COM").status_code == 409
    with Session(database) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Wallet)) == 1


def test_duplicate_profile_email_preserves_previous_data(client):
    register(client)
    register(client, "other@example.com")
    headers = login(client)
    response = client.patch(
        "/users/me",
        headers=headers,
        json={"name": "Should rollback", "email": "other@example.com"},
    )
    assert response.status_code == 409
    original = client.get("/users/me", headers=headers).json()
    assert original["email"] == "user@example.com"
    assert original["name"] == "Usuário Teste"


@pytest.mark.parametrize(
    "patch",
    [
        {"role": "auctioneer"},
        {"active": False},
        {"name": None},
        {"email": None},
        {"name": "   "},
        {"password_hash": "injected"},
    ],
)
def test_profile_rejects_mass_assignment_and_invalid_data(client, patch):
    register(client)
    headers = login(client)
    assert client.patch("/users/me", headers=headers, json=patch).status_code == 422
    assert client.get("/users/me", headers=headers).json()["role"] == "bidder"


def test_validation_never_echoes_password_and_unknown_fields(client):
    marker = "private-password-marker"
    invalid = client.post(
        "/users",
        json={
            "name": "",
            "email": "not-email",
            "password": marker,
            "role": "admin",
            "unexpected": marker,
        },
    )
    assert invalid.status_code == 422
    assert marker not in invalid.text
    short = client.post(
        "/users", json={"name": "A", "email": "a@example.com", "password": "short"}
    )
    assert short.status_code == 422
    assert '"input"' not in short.text


def test_private_endpoints_require_authentication_and_no_user_listing(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/wallets/me").status_code == 401
    assert client.patch("/users/me", json={"name": "X"}).status_code == 401
    assert client.delete("/users/me").status_code == 401
    assert client.get("/users").status_code == 405


def test_login_failures_do_not_reveal_whether_account_exists(client):
    register(client)
    bad_password = client.post(
        "/auth/token", data={"username": "user@example.com", "password": "wrong"}
    )
    missing_user = client.post(
        "/auth/token", data={"username": "missing@example.com", "password": "wrong"}
    )
    assert bad_password.status_code == missing_user.status_code == 401
    assert bad_password.json() == missing_user.json()
    assert bad_password.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "kind", ["expired", "wrong-key", "missing-claims", "unknown-user", "malformed"]
)
def test_invalid_tokens_are_rejected(client, kind):
    registered = register(client).json()
    now = datetime.now(UTC)
    payload = {
        "sub": registered["id"],
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=1),
        "iss": "auction-house",
        "aud": "auction-house-api",
    }
    key = get_settings().auth_secret.get_secret_value()
    if kind == "expired":
        payload["exp"] = now - timedelta(minutes=1)
    if kind == "wrong-key":
        key = "wrong-key-" + "y" * 40
    if kind == "missing-claims":
        payload.pop("exp")
    if kind == "unknown-user":
        payload["sub"] = str(uuid4())
    token = (
        jwt.encode(payload, key, algorithm="HS256")
        if kind != "malformed"
        else "invalid-token"
    )
    assert (
        client.get(
            "/users/me", headers={"Authorization": "Bearer " + token}
        ).status_code
        == 401
    )


def test_auctioneer_summary_requires_role_and_is_scoped_to_owner(client, database):
    first = register(client, "seller@example.com", "auctioneer").json()
    register(client, "seller2@example.com", "auctioneer")
    register(client)
    now = datetime.now(UTC)
    with Session(database) as session, session.begin():
        session.add(
            Lot(
                seller_id=first["id"],
                source_provider="test",
                external_item_id="test",
                source_url="https://example.com/item",
                item_title="Test",
                local_image_key="test.webp",
                opening_bid_cents=100,
                min_increment_cents=10,
                starts_at=now,
                original_ends_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
            )
        )
    assert (
        client.get("/auctioneers/me/summary", headers=login(client)).status_code == 403
    )
    summary = client.get(
        "/auctioneers/me/summary", headers=login(client, "seller@example.com")
    )
    assert summary.status_code == 200
    assert summary.json() == {"total_lots": 1, "total_received_cents": 0}
    assert (
        client.get(
            "/auctioneers/me/summary", headers=login(client, "seller2@example.com")
        ).json()["total_lots"]
        == 0
    )


def test_seed_is_idempotent_and_preserves_existing_accounts(database):
    with Session(database) as session, session.begin():
        assert seed_users(session) == 3
    with Session(database) as session, session.begin():
        user = session.scalar(select(User).where(User.email == "cliente1@example.com"))
        user.active = False
        user.password_hash = password_hash.hash("ChangedPassword2026!")
        wallet = session.scalar(select(Wallet).where(Wallet.user_id == user.id))
        wallet.balance_cents = 123
    with Session(database) as session, session.begin():
        assert seed_users(session) == 0
        user = session.scalar(select(User).where(User.email == "cliente1@example.com"))
        assert user.active is False
        assert password_hash.verify("ChangedPassword2026!", user.password_hash)
        assert (
            session.scalar(
                select(Wallet).where(Wallet.user_id == user.id)
            ).balance_cents
            == 123
        )
        assert session.scalar(select(func.count()).select_from(User)) == 3
        assert session.scalar(select(func.count()).select_from(Wallet)) == 3
        demo = session.scalar(select(User).where(User.email == "leiloeiro@example.com"))
        assert password_hash.verify(DEMO_PASSWORD, demo.password_hash)


def test_swagger_exposes_oauth_login_and_crud_routes(client):
    schema = client.get("/openapi.json").json()
    assert (
        schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"][
            "password"
        ]["tokenUrl"]
        == "auth/token"
    )
    assert set(schema["paths"]["/users/me"]) >= {"get", "patch", "delete"}
