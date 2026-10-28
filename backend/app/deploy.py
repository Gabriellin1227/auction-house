"""Single-instance Render entrypoint: migrations, API and closing worker."""

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Event

logger = logging.getLogger(__name__)


def prepare_storage():
    # A newly mounted disk may be root-owned. Drop privileges before running code
    # that handles HTTP requests, database migrations or external catalogue data.
    roots = [Path(os.environ[name]) for name in ("MEDIA_DIR", "AUDIT_DIR")]
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        if os.getuid() == 0:
            os.chown(root, 10001, 10001)
    if os.getuid() == 0:
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    for root in roots:
        probe = root / f".write-check-{os.getpid()}"
        try:
            with probe.open("x"):
                pass
        finally:
            probe.unlink(missing_ok=True)


def supervise(commands, stop, *, one_shot=False):
    """Stop the entire service when either essential child exits."""
    processes = []
    try:
        for command in commands:
            if stop.is_set():
                return 0
            processes.append(subprocess.Popen(command))
        while not stop.wait(0.2):
            for process in processes:
                code = process.poll()
                if code is not None:
                    if one_shot and code == 0:
                        return 0
                    logger.error("Processo essencial encerrou; reiniciando o serviço")
                    return code if code > 0 else 1
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + 20
        for process in processes:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    logging.basicConfig(level=logging.INFO)
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        # Fail before migration instead of silently using the local default DB.
        if not os.environ.get("DATABASE_URL"):
            raise ValueError("DATABASE_URL é obrigatória no deploy")
        prepare_storage()
        from app.config import get_settings

        settings = get_settings()
        if not settings.auth_secret or not settings.audit_secret:
            raise ValueError("AUTH_SECRET e AUDIT_SECRET são obrigatórios")
        if settings.auth_secret == settings.audit_secret:
            raise ValueError("Use chaves diferentes para autenticação e auditoria")
        if not settings.cors_origins or not settings.worker_required:
            raise ValueError("Configure CORS_ORIGINS e WORKER_REQUIRED=true")
        port = int(os.getenv("PORT", "10000"))
        if not 1 <= port <= 65535:
            raise ValueError("PORT inválida")
        # Migrations don't need the disk, but running here guarantees completion
        # before either process starts. Never seed public demo accounts implicitly.
        result = supervise(
            [["alembic", "-c", "alembic.ini", "upgrade", "head"]],
            stop,
            one_shot=True,
        )
        if result or stop.is_set():
            return result
        from app.worker import HEARTBEAT

        HEARTBEAT.unlink(missing_ok=True)
        return supervise(
            [
                [sys.executable, "-m", "app.worker"],
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(port),
                    "--workers",
                    "1",
                ],
            ],
            stop,
        )
    except Exception:
        logger.error(
            "Falha na preparação do deploy; confira configuração e armazenamento"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
