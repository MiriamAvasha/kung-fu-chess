import asyncio
import contextlib

import websockets

from server.websocket.config import HOST, PORT
from server.websocket.game_server import GameServer


async def main(host: str = HOST, port: int = PORT) -> None:
    """Start the WebSocket listener and room ticker."""
    game_server = GameServer()
    ticker = asyncio.create_task(game_server.run_ticker())
    try:
        async with websockets.serve(
            game_server.handle_client,
            host,
            port,
        ):
            print(
                'WebSocket server running on ws://{}:{}'.format(
                    host,
                    port,
                )
            )
            await asyncio.Future()
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker
        game_server.close()
