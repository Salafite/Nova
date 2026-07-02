import json
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._rooms = defaultdict(set)

    async def connect(self, room: str, ws: WebSocket):
        await ws.accept()
        self._rooms[room].add(ws)

    def disconnect(self, room: str, ws: WebSocket):
        self._rooms[room].discard(ws)
        if not self._rooms[room]:
            del self._rooms[room]

    async def broadcast(self, room: str, event: str, data: dict):
        message = json.dumps({'event': event, 'data': data})
        stale = set()
        for ws in self._rooms.get(room, set()):
            try:
                await ws.send_text(message)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self._rooms[room].discard(ws)


inventory_manager = ConnectionManager()
order_manager = ConnectionManager()
