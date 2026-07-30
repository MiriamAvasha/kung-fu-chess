import asyncio
import contextlib
import signal
from pathlib import Path
from typing import Optional, Union

import websockets

from server.websocket.config import AUTO_RESIGN_SECONDS, DB_PATH, HOST, PORT
from server.websocket.game_server import GameServer


async def main(
    host: str = HOST,
    port: int = PORT,
    db_path: Optional[Union[str, Path]] = None,
    auto_resign_seconds: int = AUTO_RESIGN_SECONDS,
) -> None:
    """Start the WebSocket listener and room ticker."""
    resolved_db_path = DB_PATH if db_path is None else db_path
    game_server = GameServer(
        db_path=resolved_db_path,
        auto_resign_seconds=auto_resign_seconds,
    )
    ticker = asyncio.create_task(game_server.run_ticker())
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except (NotImplementedError, RuntimeError):
            # Windows ProactorEventLoop does not support add_signal_handler.
            signal.signal(sig, lambda *_args: request_stop())

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
            await stop_event.wait()
            print('Shutting down WebSocket server...')
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker
        game_server.close()
