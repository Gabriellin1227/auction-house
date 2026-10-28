import asyncio
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.lots.service import LotService

router = APIRouter()


def exists(engine, lot_id):
    with Session(engine) as session:
        LotService(session).get(lot_id)


async def send_updates(socket, queue):
    while True:
        try:
            message = await asyncio.wait_for(queue.get(), timeout=15)
        except TimeoutError:
            message = {"type": "ResyncRequired", "reason": "heartbeat"}
        await asyncio.wait_for(socket.send_json(message), timeout=5)


async def watch_disconnect(socket):
    while True:
        message = await socket.receive()
        if message["type"] == "websocket.disconnect":
            return
        # Commands remain HTTP-only; public sockets are receive-only channels.
        await socket.close(code=1008, reason="Envie comandos pela API HTTP")
        return


@router.websocket("/ws/lots/{lot_id}")
async def lot_room(socket: WebSocket, lot_id: UUID):
    hub = socket.app.state.room_hub
    try:
        queue = hub.subscribe(lot_id)
    except RuntimeError:
        await socket.close(code=1013)
        return
    tasks = []
    try:
        try:
            await asyncio.to_thread(exists, socket.app.state.event_engine, lot_id)
        except HTTPException:
            await socket.close(code=1008)
            return
        # Subscribe before synchronizing: events during the HTTP snapshot queue up.
        await socket.accept()
        await socket.send_json({"type": "ResyncRequired", "reason": "connected"})
        tasks = [
            asyncio.create_task(send_updates(socket, queue)),
            asyncio.create_task(watch_disconnect(socket)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, OSError, RuntimeError, TimeoutError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        hub.unsubscribe(lot_id, queue)
