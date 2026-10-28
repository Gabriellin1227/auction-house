import argparse
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.journal import Journal
from app.audit.service import AuditService
from app.bids.signing import ZERO_HASH, head_record, sign
from app.db.models import AuditHead, Bid, Lot
from app.db.session import get_engine

logger = logging.getLogger(__name__)


def checkpoint_batch(engine, after=None):
    with Session(engine) as session:
        query = select(Lot.id).order_by(Lot.id).limit(100)
        if after is not None:
            query = query.where(Lot.id > after)
        ids = session.scalars(query).all()
    written = failed = 0
    for lot_id in ids:
        with Session(engine) as session:
            try:
                lot = session.scalar(
                    select(Lot)
                    .where(Lot.id == lot_id)
                    .with_for_update(skip_locked=True)
                )
                if lot is None:
                    continue
                result = AuditService(session).verify(lot_id)
                if (
                    result["integrity"] != "valid"
                    or result["checkpoint_status"] == "invalid"
                ):
                    raise ValueError("Auditoria não permite checkpoint")
                written += Journal().append(
                    lot_id, result["verified_count"], result["last_hash"]
                )
                session.rollback()  # No database mutations; release the lot lock.
            except Exception:
                session.rollback()
                failed += 1
                logger.error("Checkpoint pendente/inconsistente para lote %s", lot_id)
    return (ids[-1] if len(ids) == 100 else None), written, failed


def initialize_empty_heads(engine):
    """Explicit legacy bootstrap only; never reconstruct signatures of old bids."""
    count = 0
    with Session(engine) as session:
        ids = session.scalars(
            select(Lot.id).where(
                ~select(AuditHead.lot_id).where(AuditHead.lot_id == Lot.id).exists()
            )
        ).all()
    for lot_id in ids:
        with Session(engine) as session, session.begin():
            lot = session.scalar(select(Lot).where(Lot.id == lot_id).with_for_update())
            if session.get(AuditHead, lot_id) or lot.current_bid_id:
                continue
            if session.scalar(select(Bid.id).where(Bid.lot_id == lot_id).limit(1)):
                continue
            session.add(
                AuditHead(
                    lot_id=lot_id,
                    last_sequence=0,
                    last_hash=ZERO_HASH,
                    key_version=1,
                    signature=sign(head_record(lot_id, 0, ZERO_HASH)),
                )
            )
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Checkpoints de auditoria")
    parser.add_argument("--init-empty-heads", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    engine = get_engine()
    if args.init_empty_heads:
        print(f"Cabeçalhos iniciais criados: {initialize_empty_heads(engine)}")
        return
    cursor = None
    failed_total = 0
    while True:
        cursor, written, failed = checkpoint_batch(engine, cursor)
        failed_total += failed
        print(f"Checkpoints gravados: {written}; pendentes/inconsistentes: {failed}")
        if cursor is None:
            break
    raise SystemExit(1 if failed_total else 0)


if __name__ == "__main__":
    main()
