from typing import Any, Set

from websockets.exceptions import ConnectionClosed

from server.rooms import Room
from shared.activity_log import log_activity
from shared.messages.parsers import message_to_dict
from shared.protocol import encode_message


class WebSocketTransport:
    """Encode, log, send, and broadcast WebSocket messages."""

    def __init__(self, clients: Set[Any], logger):
        self.clients = clients
        self.logger = logger

    def log(self, direction: str, payload: str) -> None:
        log_activity(self.logger, direction, payload)

    async def send(self, websocket: Any, message: Any) -> None:
        encoded = encode_message(message_to_dict(message))
        self.log('OUT', encoded)
        try:
            await websocket.send(encoded)
        except ConnectionClosed:
            pass

    async def broadcast_room(self, room: Room, message: Any) -> None:
        encoded = encode_message(message_to_dict(message))
        self.log('OUT', encoded)
        disconnected = []

        for client in room.connections:
            try:
                await client.send(encoded)
            except ConnectionClosed:
                disconnected.append(client)

        for client in disconnected:
            self.clients.discard(client)
