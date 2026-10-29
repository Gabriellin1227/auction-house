import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect
from test_bids_api import offer

from app.db.models import OutboxEvent
from app.events.hub import RoomHub
from app.events.publisher import OutboxPublisher


def test_outbox_survives_new_session_and_is_not_republished(client, database, market):
    assert offer(client, market).status_code == 201
    delivered = []
    with Session(database) as session:
        assert OutboxPublisher(session).run_once(delivered.append) == 1
    assert len(delivered) == 1
    envelope = delivered[0]
    assert envelope["type"] == "BidAccepted"
    assert envelope["version"] == 1
    assert "@example.com" not in str(envelope)
    assert all(str(uid) not in str(envelope) for uid in market["users"])
    with Session(database) as session:
        event = session.scalar(select(OutboxEvent))
        assert event.published_at is not None and event.attempts == 1
        assert OutboxPublisher(session).run_once(delivered.append) == 0
    assert len(delivered) == 1


def test_failed_publication_retries_after_backoff(client, database, market):
    assert offer(client, market).status_code == 201

    def unavailable(envelope):
        raise OSError("publisher unavailable")

    with Session(database) as session:
        assert OutboxPublisher(session).run_once(unavailable) == 1
        event = session.scalar(select(OutboxEvent))
        assert event.published_at is None and event.attempts == 1
        assert OutboxPublisher(session).run_once(unavailable) == 0
        event.next_attempt_at = session.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)
        session.commit()
    delivered = []
    with Session(database) as session:
        assert OutboxPublisher(session).run_once(delivered.append) == 1
        event = session.scalar(select(OutboxEvent))
        assert event.published_at is not None and event.attempts == 2
    assert len(delivered) == 1


def test_uncommitted_event_is_invisible_to_publisher(client, database, market):
    with Session(database) as writer:
        writer.add(
            OutboxEvent(
                lot_id=market["lots"][0],
                aggregate_version=1,
                event_type="BidAccepted",
                payload={},
            )
        )
        writer.flush()
        with Session(database) as reader:
            assert (
                OutboxPublisher(reader).run_once(lambda _: pytest.fail("uncommitted"))
                == 0
            )
        writer.rollback()
    with Session(database) as reader:
        assert (
            OutboxPublisher(reader).run_once(lambda _: pytest.fail("rolled back")) == 0
        )


def test_locked_events_are_not_claimed_twice(client, database, market):
    assert offer(client, market).status_code == 201
    with Session(database) as first:
        first.scalar(select(OutboxEvent).with_for_update())
        with Session(database) as second:
            assert (
                OutboxPublisher(second).run_once(lambda _: pytest.fail("locked")) == 0
            )
        first.rollback()
    with Session(database) as second:
        assert OutboxPublisher(second).run_once(lambda _: None) == 1


def test_hub_isolates_rooms_bounds_queue_and_unsubscribes():
    async def scenario():
        a, b = uuid4(), uuid4()
        hub = RoomHub(queue_size=1, max_connections=2)
        qa, qb = hub.subscribe(a), hub.subscribe(b)
        with pytest.raises(RuntimeError):
            hub.subscribe(a)
        envelope = {"lot_id": str(a), "version": 1}
        await hub.publish(envelope)
        assert qb.empty()
        await hub.publish(envelope)
        assert qa.qsize() == 1
        assert (await qa.get())["type"] == "ResyncRequired"
        hub.unsubscribe(a, qa)
        hub.unsubscribe(a, qa)
        hub.unsubscribe(b, qb)
        assert not hub.rooms and hub.connections == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("client", [True], indirect=True)
def test_two_rooms_receive_committed_bid_and_reconnect(client, database, market):
    path = f"/ws/lots/{market['lots'][0]}"
    with client.websocket_connect(path) as a, client.websocket_connect(path) as b:
        assert a.receive_json()["type"] == "ResyncRequired"
        assert b.receive_json()["type"] == "ResyncRequired"
        response = offer(client, market)
        assert response.status_code == 201, response.text
        event_a, event_b = a.receive_json(), b.receive_json()
        assert event_a == event_b
        assert event_a["type"] == "BidAccepted"
        assert event_a["payload"]["amount_cents"] == 8000
        assert event_a["event_id"]
    assert offer(client, market, 9000, bidder=2).status_code == 201
    with client.websocket_connect(path) as reconnect:
        assert reconnect.receive_json()["type"] == "ResyncRequired"
        fresh = client.get(f"/lots/{market['lots'][0]}").json()
        assert fresh["currentBid"] == 9000 and fresh["version"] == 2


def test_public_socket_rejects_unknown_lot_and_commands(client, market):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/lots/{uuid4()}"):
            pass
    with client.websocket_connect(f"/ws/lots/{market['lots'][0]}") as socket:
        assert socket.receive_json()["type"] == "ResyncRequired"
        socket.send_json({"amount_cents": 8000})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1008


def test_repeated_socket_cancellation_releases_room_capacity(monkeypatch):
    from contextlib import suppress
    from types import SimpleNamespace

    from app.events.router import lot_room

    monkeypatch.setattr("app.events.router.exists", lambda *_: None)

    async def scenario():
        connected, cleaning, never = asyncio.Event(), asyncio.Event(), asyncio.Event()
        hub = RoomHub(max_connections=1)

        class Socket:
            app = SimpleNamespace(
                state=SimpleNamespace(room_hub=hub, event_engine=None)
            )

            async def accept(self):
                pass

            async def send_json(self, message):
                connected.set()

            async def receive(self):
                try:
                    await never.wait()
                finally:
                    cleaning.set()
                    await never.wait()

        task = asyncio.create_task(lot_room(Socket(), uuid4()))
        await asyncio.wait_for(connected.wait(), 2)
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.wait_for(cleaning.wait(), 2)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        assert hub.connections == 0 and not hub.rooms
        # Capacity remains usable after forced shutdown, without restarting API.
        replacement = uuid4()
        queue = hub.subscribe(replacement)
        hub.unsubscribe(replacement, queue)

    asyncio.run(scenario())
