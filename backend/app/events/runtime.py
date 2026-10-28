import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_engine
from app.events.hub import RoomHub
from app.events.publisher import OutboxPublisher

logger = logging.getLogger(__name__)


def dispatch_batch(engine, hub, loop):
    def deliver(envelope):
        future = asyncio.run_coroutine_threadsafe(hub.publish(envelope), loop)
        try:
            future.result(timeout=5)
        except Exception:
            future.cancel()
            raise

    with Session(engine) as session:
        return OutboxPublisher(session).run_once(deliver)


async def publish_loop(engine, hub, stop):
    loop = asyncio.get_running_loop()
    while not stop.is_set():
        try:
            await asyncio.to_thread(dispatch_batch, engine, hub, loop)
        except Exception:
            logger.warning("Publicação da outbox indisponível; nova tentativa agendada")
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.5)
        except TimeoutError:
            pass


@asynccontextmanager
async def lifespan(app):
    hub = RoomHub()
    app.state.room_hub = hub
    app.state.event_engine = get_engine()
    stop = asyncio.Event()
    task = (
        asyncio.create_task(publish_loop(app.state.event_engine, hub, stop))
        if get_settings().events_enabled
        else None
    )
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task
