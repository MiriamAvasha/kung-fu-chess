from typing import Any, AsyncIterator, Dict

import websockets

from client.network.config import DEFAULT_URI, client_logger
from shared.activity_log import log_activity
from shared.protocol import encode_message


class GameConnection:
    """Raw WebSocket transport used by the client application."""

    def __init__(
        self,
        websocket: Any,
        uri: str = DEFAULT_URI,
        logger=None,
    ):
        self.websocket = websocket
        self.uri = uri
        self._logger = logger or client_logger

    @classmethod
    async def open(cls, uri: str = DEFAULT_URI, logger=None):
        websocket = await websockets.connect(uri)
        return cls(websocket, uri=uri, logger=logger)

    async def close(self) -> None:
        await self.websocket.close()

    async def send_raw(self, payload: str) -> None:
        log_activity(self._logger, 'OUT', payload)
        await self.websocket.send(payload)

    async def send_message(self, message: Dict[str, Any]) -> None:
        await self.send_raw(encode_message(message))

    async def receive_raw(self) -> str:
        raw_message = await self.websocket.recv()
        log_activity(self._logger, 'IN', raw_message)
        return raw_message

    async def incoming(self) -> AsyncIterator[str]:
        async for raw_message in self.websocket:
            log_activity(self._logger, 'IN', raw_message)
            yield raw_message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
