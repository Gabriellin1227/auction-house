import asyncio
from collections import defaultdict
from uuid import UUID


class RoomHub:
    """Event-loop-owned fanout. No balances, authentication or database decisions."""

    def __init__(self, queue_size=64, max_connections=500):
        self.rooms: dict[UUID, set[asyncio.Queue]] = defaultdict(set)
        self.queue_size = queue_size
        self.max_connections = max_connections
        self.connections = 0

    def subscribe(self, lot_id: UUID):
        if self.connections >= self.max_connections:
            raise RuntimeError("Limite de conexões atingido")
        queue = asyncio.Queue(maxsize=self.queue_size)
        self.rooms[lot_id].add(queue)
        self.connections += 1
        return queue

    def unsubscribe(self, lot_id: UUID, queue):
        room = self.rooms.get(lot_id)
        if room and queue in room:
            room.remove(queue)
            self.connections -= 1
            if not room:
                del self.rooms[lot_id]

    async def publish(self, envelope: dict):
        for queue in tuple(self.rooms.get(UUID(envelope["lot_id"]), ())):
            if queue.full():
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({"type": "ResyncRequired", "reason": "slow_client"})
            else:
                queue.put_nowait(envelope)
