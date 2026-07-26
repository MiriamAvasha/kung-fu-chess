import asyncio
import contextlib
import time
from typing import Any, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

from engine.game_factory import build_engine
from server.auth import AuthError, AuthService, UserRepository
from server.db import open_database
from server.game_session import GameSession
from server.lobby import Lobby, LobbyError
from server.rating import RatingService
from shared.messages.client_messages import JoinRequest, MoveRequest
from shared.messages.errors import ProtocolError
from shared.messages.parsers import message_to_dict, parse_client_message
from shared.messages.server_messages import (
    ErrorMessage,
    JoinAccepted,
    RatingUpdate,
)
from shared.protocol import encode_message, error_message


HOST = 'localhost'
PORT = 8765
TICK_SECONDS = 0.05


class GameServer:
    def __init__(
        self,
        session: Optional[GameSession] = None,
        auth_service: Optional[AuthService] = None,
        rating_service: Optional[RatingService] = None,
        db_path=None,
    ):
        self.session = session or GameSession(build_engine())
        self.lobby = Lobby()
        self.clients: Set[Any] = set()
        self._game_started = False
        self._ratings_applied = False

        if auth_service is not None and rating_service is not None:
            self._auth_service = auth_service
            self._rating_service = rating_service
            self._db_connection = None
        else:
            self._db_connection = open_database(db_path)
            repository = UserRepository(self._db_connection)
            self._auth_service = auth_service or AuthService(repository)
            self._rating_service = rating_service or RatingService(repository)

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        print('Client connected')
        try:
            async for raw_message in websocket:
                if not isinstance(raw_message, str):
                    await self._send(
                        websocket,
                        error_message(
                            'invalid_command',
                            'message must be text JSON',
                        ),
                    )
                    continue

                try:
                    message = parse_client_message(raw_message)
                except ProtocolError as error:
                    await self._send(
                        websocket,
                        ErrorMessage('invalid_command', str(error)).to_dict(),
                    )
                    continue

                if isinstance(message, JoinRequest):
                    await self._handle_join(websocket, message)
                elif isinstance(message, MoveRequest):
                    await self._handle_move(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            self.lobby.leave(websocket)
            self.clients.discard(websocket)
            print('Client disconnected')

    async def _handle_join(self, websocket, message: JoinRequest):
        try:
            account = self._auth_service.login_or_register(
                message.username,
                message.password,
            )
            player = self.lobby.try_join(
                account.username,
                account.rating,
                websocket,
            )
        except AuthError as error:
            await self._send(
                websocket,
                ErrorMessage(error.code, error.message).to_dict(),
            )
            return
        except LobbyError as error:
            await self._send(
                websocket,
                ErrorMessage(error.code, error.message).to_dict(),
            )
            return

        accepted = JoinAccepted(
            username=player.username,
            color=player.color,
            rating=player.rating,
            players=self.lobby.player_infos(),
        )
        await self._send(websocket, accepted.to_dict())
        print(
            'Player joined: {} as {} (rating {})'.format(
                player.username,
                'White' if player.color == 'w' else 'Black',
                player.rating,
            )
        )

        if self.lobby.is_ready() and not self._game_started:
            self._game_started = True
            await self._broadcast(self.session.initial_message())

    async def _handle_move(self, websocket, message: MoveRequest):
        player = self.lobby.get_player(websocket)
        if player is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'join the lobby before sending moves',
                ).to_dict(),
            )
            return

        if not self.lobby.is_ready():
            await self._send(
                websocket,
                ErrorMessage(
                    'game_not_ready',
                    'waiting for a second player to join',
                ).to_dict(),
            )
            return

        result = self.session.handle_command(
            message.command,
            player.color,
        )
        await self._send(websocket, result)
        if (
            result.get('type') == 'move_result'
            and result.get('accepted')
        ):
            await self.broadcast_game_state()
            await self._maybe_apply_ratings()

    async def run_ticker(self):
        previous = time.monotonic()
        while True:
            await asyncio.sleep(TICK_SECONDS)
            if not self._game_started:
                previous = time.monotonic()
                continue
            current = time.monotonic()
            elapsed_ms = max(1, int((current - previous) * 1000))
            previous = current
            if self.session.advance(elapsed_ms):
                await self.broadcast_game_state()
                await self._maybe_apply_ratings()

    async def broadcast_game_state(self):
        await self._broadcast(self.session.game_state_message())

    async def _maybe_apply_ratings(self):
        if self._ratings_applied or not self.session.is_game_over:
            return

        winner_color = self.session.winner_color()
        if winner_color is None:
            return

        winner = self.lobby.get_by_color(winner_color)
        loser_color = 'b' if winner_color == 'w' else 'w'
        loser = self.lobby.get_by_color(loser_color)
        if winner is None or loser is None:
            return

        ratings = self._rating_service.apply_match_result(
            winner.username,
            loser.username,
        )
        self.lobby.update_ratings(ratings)
        self._ratings_applied = True
        await self._broadcast(
            RatingUpdate(
                winner=winner.username,
                loser=loser.username,
                ratings=ratings,
            )
        )

    async def _broadcast(self, message):
        if not self.clients:
            return

        encoded = encode_message(message_to_dict(message))
        disconnected = set()
        for client in tuple(self.clients):
            try:
                await client.send(encoded)
            except ConnectionClosed:
                disconnected.add(client)
        self.clients.difference_update(disconnected)

    async def _send(self, websocket, message):
        await websocket.send(encode_message(message_to_dict(message)))

    def close(self):
        if self._db_connection is not None:
            self._db_connection.close()
            self._db_connection = None


async def main(host: str = HOST, port: int = PORT):
    game_server = GameServer()
    ticker = asyncio.create_task(game_server.run_ticker())
    try:
        async with websockets.serve(
            game_server.handle_client,
            host,
            port,
        ):
            print(f'WebSocket server running on ws://{host}:{port}')
            await asyncio.Future()
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker
        game_server.close()
