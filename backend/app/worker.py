"""Independent, restartable closing worker. No browser or HTTP request required."""

import argparse
import logging
import signal
import time
from pathlib import Path
from threading import Event

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.checkpoints import checkpoint_batch
from app.db.models import Lot
from app.db.session import get_engine
from app.settlements.service import SettlementService

logger = logging.getLogger(__name__)
HEARTBEAT = Path("/tmp/auction-worker-heartbeat")


def run_once(engine, progress=lambda: None):
    with Session(engine) as session:
        ids = session.scalars(
            select(Lot.id)
            .where(
                Lot.status.in_(["scheduled", "live"]),
                Lot.ends_at <= func.clock_timestamp(),
            )
            .order_by(Lot.ends_at, Lot.id)
            .limit(100)
        ).all()
    closed = failed = 0
    for lot_id in ids:
        progress()
        with Session(engine) as session:
            try:
                closed += SettlementService(session).close(lot_id)
            except Exception:
                failed += 1
                logger.error(
                    "Fechamento pendente para lote %s; nova tentativa no próximo ciclo",
                    lot_id,
                )
    return closed, failed


def heartbeat():
    HEARTBEAT.write_text(str(time.time()))


def worker_alive():
    try:
        age = time.time() - float(HEARTBEAT.read_text())
        return 0 <= age < 30
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Encerrar e liquidar leilões vencidos")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        raise SystemExit(0 if worker_alive() else 1)
    logging.basicConfig(level=logging.INFO)
    engine = get_engine()
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    cursor = None
    while not stop.is_set():
        heartbeat()
        try:
            closed, failed = run_once(engine, heartbeat)
            cursor, _, checkpoint_failed = checkpoint_batch(engine, cursor)
            failed += checkpoint_failed
        except Exception:
            closed, failed = 0, 1
            logger.error(
                "Banco indisponível; fechamento será retomado no próximo ciclo"
            )
        heartbeat()
        if closed:
            logger.info("Lotes encerrados neste ciclo: %s", closed)
        if args.once:
            raise SystemExit(1 if failed else 0)
        stop.wait(1)


if __name__ == "__main__":
    main()
