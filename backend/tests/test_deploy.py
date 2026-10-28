import json
import subprocess
import sys
import time
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deploy import supervise
from app.main import create_app
from app.worker import worker_alive


@pytest.fixture
def deployment_app(monkeypatch, tmp_path):
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(["https://yorknew.vercel.app"]))
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path / "media"))
    get_settings.cache_clear()
    try:
        yield create_app()
    finally:
        get_settings.cache_clear()


def test_cross_origin_auth_and_deposit_headers(deployment_app):
    client = TestClient(deployment_app)
    response = client.options(
        "/wallets/me/deposits",
        headers={
            "Origin": "https://yorknew.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "authorization,content-type,idempotency-key"
            ),
        },
    )
    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://yorknew.vercel.app"
    )
    assert "access-control-allow-credentials" not in response.headers
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_origin_and_methods_rejected(deployment_app):
    client = TestClient(deployment_app)
    for origin, method in [
        ("https://other.vercel.app", "POST"),
        ("https://yorknew.vercel.app", "PUT"),
    ]:
        response = client.options(
            "/users",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
            },
        )
        assert response.status_code == 400
    response = client.get("/health", headers={"Origin": "https://other.vercel.app"})
    assert "access-control-allow-origin" not in response.headers


def test_readiness_includes_worker_in_bundled_deployment(client, monkeypatch, database):
    monkeypatch.setenv("WORKER_REQUIRED", "true")
    monkeypatch.setattr("app.main.get_engine", lambda: database)
    monkeypatch.setattr("app.worker.worker_alive", lambda: False)
    get_settings.cache_clear()
    assert client.get("/ready").status_code == 503
    monkeypatch.setattr("app.worker.worker_alive", lambda: True)
    assert client.get("/ready").status_code == 200


def test_heartbeat_rejects_missing_expired_and_future_timestamp(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"
    monkeypatch.setattr("app.worker.HEARTBEAT", path)
    assert not worker_alive()
    for content in ["invalid", str(time.time() - 60), str(time.time() + 60)]:
        path.write_text(content)
        assert not worker_alive()
    path.write_text(str(time.time()))
    assert worker_alive()


def test_supervisor_stops_other_child_after_failure(monkeypatch):
    processes = []
    original = subprocess.Popen

    def track(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr("app.deploy.subprocess.Popen", track)
    result = supervise(
        [
            [sys.executable, "-c", "import time; time.sleep(60)"],
            [sys.executable, "-c", "raise SystemExit(7)"],
        ],
        Event(),
    )
    assert result == 7
    assert len(processes) == 2 and all(p.poll() is not None for p in processes)


def test_failed_migration_blocks_daemon_start():
    assert (
        supervise(
            [[sys.executable, "-c", "raise SystemExit(3)"]],
            Event(),
            one_shot=True,
        )
        == 3
    )
    assert (
        supervise(
            [[sys.executable, "-c", "pass"]],
            Event(),
            one_shot=True,
        )
        == 0
    )
