from fastapi.testclient import TestClient

from app.main import app


def test_health_is_public_and_returns_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_does_not_expose_database_errors(monkeypatch):
    from sqlalchemy.exc import OperationalError

    def unavailable():
        raise OperationalError("secret connection", {}, Exception("password"))

    monkeypatch.setattr("app.main.get_engine", unavailable)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Banco de dados indisponível"}
