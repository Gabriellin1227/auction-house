from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import OutboxEvent


class OutboxPublisher:
    def __init__(self, session: Session):
        self.session = session

    def run_once(self, deliver: Callable[[dict], None]) -> int:
        now = self.session.scalar(select(func.clock_timestamp()))
        events = self.session.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.published_at.is_(None),
                OutboxEvent.next_attempt_at <= now,
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(50)
            .with_for_update(skip_locked=True)
        ).all()
        for event in events:
            event.attempts += 1
            try:
                deliver(
                    {
                        "type": event.event_type,
                        "event_id": str(event.id),
                        "lot_id": str(event.lot_id),
                        "version": event.aggregate_version,
                        "payload": event.payload,
                    }
                )
            except Exception:
                # No exception text/payload in logs: public stream must stay private.
                event.next_attempt_at = now + timedelta(
                    seconds=min(2 ** min(event.attempts, 6), 60)
                )
            else:
                event.published_at = self.session.scalar(select(func.clock_timestamp()))
        self.session.commit()
        return len(events)
