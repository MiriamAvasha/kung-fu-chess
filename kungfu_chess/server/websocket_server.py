import asyncio
import contextlib
import time
from typing import Any, Dict, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

from engine.game_factory import build_engine
from server.auth import AuthError, AuthService, UserAccount, UserRepository
from server.db import open_database
from server.game_session import GameSession
from server.lobby import Lobby
from server.matchmaking import (
    ELO_RANGE,
    SEARCH_TIMEOUT_SECONDS,
    Matchmaker,
    QueueEntry,
)
from server.rating import RatingService
from shared.messages.client_messages import JoinRequest, MoveRequest, PlayRequest
from shared.messages.errors import ProtocolError
from shared.messages.parsers import message_to_dict, parse_client_message
from shared.messages.server_messages import (
    DisconnectCountdown,
    ErrorMessage,
    JoinAccepted,
    MatchFound,
    NoMatch,
    QueueStatus,
    RatingUpdate,
)
from shared.protocol import encode_message, error_message


HOST = 'localhost'
PORT = 8765
TICK_SECONDS = 0.05
AUTO_RESIGN_SECONDS = 20


class GameServer:
    def __init__(
        self,
        session: Optional[GameSession] = None,
        auth_service: Optional[AuthService] = None,
        rating_service: Optional[RatingService] = None,
        matchmaker: Optional[Matchmaker] = None,
        db_path=None,
        auto_resign_seconds: int = AUTO_RESIGN_SECONDS,
    ):
        self.session = session or GameSession(build_engine())
        self.lobby = Lobby()
        self.matchmaker = matchmaker or Matchmaker()
        self.clients: Set[Any] = set()
        self._accounts: Dict[Any, UserAccount] = {}
        self._game_started = False
        self._ratings_applied = False
        self._auto_resign_seconds = auto_resign_seconds
        self._disconnect_deadline: Optional[float] = None
        self._disconnect_player = None
        self._last_countdown_second: Optional[int] = None

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
                elif isinstance(message, PlayRequest):
                    await self._handle_play(websocket)
                elif isinstance(message, MoveRequest):
                    await self._handle_move(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            await self._handle_disconnect(websocket)
            self.clients.discard(websocket)
            print('Client disconnected')

    async def _handle_join(self, websocket, message: JoinRequest):
        if websocket in self._accounts:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_joined',
                    'already logged in on this connection',
                ).to_dict(),
            )
            return

        try:
            account = self._auth_service.login_or_register(
                message.username,
                message.password,
            )
        except AuthError as error:
            await self._send(
                websocket,
                ErrorMessage(error.code, error.message).to_dict(),
            )
            return

        self._accounts[websocket] = account
        await self._send(
            websocket,
            JoinAccepted(account.username, account.rating).to_dict(),
        )
        print(
            'Player logged in: {} (rating {})'.format(
                account.username,
                account.rating,
            )
        )

    async def _handle_play(self, websocket):
        account = self._accounts.get(websocket)
        if account is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before pressing Play',
                ).to_dict(),
            )
            return

        if self.lobby.get_player(websocket) is not None:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_in_game',
                    'already seated in a match',
                ).to_dict(),
            )
            return

        # Refresh rating from DB in case it changed.
        fresh = self._auth_service.get_account(account.username)
        if fresh is not None:
            account = fresh
            self._accounts[websocket] = account

        entry = QueueEntry(account.username, account.rating, websocket)
        try:
            matched = self.matchmaker.enqueue(entry)
        except ValueError:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_searching',
                    'already searching for a match',
                ).to_dict(),
            )
            return

        if matched is None:
            await self._send(
                websocket,
                QueueStatus(
                    timeout_seconds=SEARCH_TIMEOUT_SECONDS,
                    elo_range=ELO_RANGE,
                ).to_dict(),
            )
            return

        white_entry, black_entry = matched
        await self._start_match(white_entry, black_entry)

    async def _start_match(self, white_entry: QueueEntry, black_entry: QueueEntry):
        self.session = GameSession(build_engine())
        self._game_started = True
        self._ratings_applied = False
        self._clear_disconnect_timer()

        self.lobby.seat_match(
            white_entry.username,
            white_entry.rating,
            white_entry.connection,
            black_entry.username,
            black_entry.rating,
            black_entry.connection,
        )

        players = self.lobby.player_infos()
        for player in self.lobby.players:
            await self._send(
                player.connection,
                MatchFound(
                    username=player.username,
                    color=player.color,
                    rating=player.rating,
                    players=players,
                ).to_dict(),
            )
            await self._send(player.connection, self.session.initial_message())

        print(
            'Match started: {} (White) vs {} (Black)'.format(
                white_entry.username,
                black_entry.username,
            )
        )

    async def _handle_move(self, websocket, message: MoveRequest):
        player = self.lobby.get_player(websocket)
        if player is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'join a match before sending moves',
                ).to_dict(),
            )
            return

        if not self.lobby.is_ready() or not self._game_started:
            await self._send(
                websocket,
                ErrorMessage(
                    'game_not_ready',
                    'waiting for match to start',
                ).to_dict(),
            )
            return

        if self.session.is_game_over:
            await self._send(
                websocket,
                ErrorMessage('game_over', 'game already finished').to_dict(),
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

    async def _handle_disconnect(self, websocket):
        self.matchmaker.remove(websocket)
        account = self._accounts.pop(websocket, None)
        player = self.lobby.get_player(websocket)

        if (
            player is not None
            and self._game_started
            and not self.session.is_game_over
            and self.lobby.is_ready()
        ):
            self._disconnect_deadline = (
                time.monotonic() + self._auto_resign_seconds
            )
            self._disconnect_player = player
            self._last_countdown_second = None
            await self._broadcast(
                DisconnectCountdown(
                    username=player.username,
                    seconds_remaining=self._auto_resign_seconds,
                    total_seconds=self._auto_resign_seconds,
                )
            )
            print(
                'Player disconnected during game: {} — auto-resign in {}s'.format(
                    player.username,
                    self._auto_resign_seconds,
                )
            )
            return

        self.lobby.leave(websocket)
        if account is not None:
            print('Player left: {}'.format(account.username))

    async def run_ticker(self):
        previous = time.monotonic()
        while True:
            await asyncio.sleep(TICK_SECONDS)
            now = time.monotonic()
            await self._expire_matchmaking(now)
            await self._tick_disconnect_countdown(now)

            if not self._game_started or self.session.is_game_over:
                previous = now
                continue

            elapsed_ms = max(1, int((now - previous) * 1000))
            previous = now
            if self.session.advance(elapsed_ms):
                await self.broadcast_game_state()
                await self._maybe_apply_ratings()

    async def _expire_matchmaking(self, now: float):
        expired = self.matchmaker.pop_expired(now)
        for entry in expired:
            await self._send(
                entry.connection,
                NoMatch('no player found').to_dict(),
            )
            print('Matchmaking timeout for {}'.format(entry.username))

    async def _tick_disconnect_countdown(self, now: float):
        if (
            self._disconnect_deadline is None
            or self._disconnect_player is None
            or self.session.is_game_over
        ):
            return

        remaining = int(max(0, self._disconnect_deadline - now))
        if (
            self._last_countdown_second is None
            or remaining != self._last_countdown_second
        ):
            self._last_countdown_second = remaining
            await self._broadcast(
                DisconnectCountdown(
                    username=self._disconnect_player.username,
                    seconds_remaining=remaining,
                    total_seconds=self._auto_resign_seconds,
                )
            )

        if remaining > 0:
            return

        loser = self._disconnect_player
        self.session.resign(loser.color)
        await self.broadcast_game_state()
        await self._maybe_apply_ratings(reason='auto_resign')
        self._clear_disconnect_timer()
        print('Auto-resign: {}'.format(loser.username))

    def _clear_disconnect_timer(self):
        self._disconnect_deadline = None
        self._disconnect_player = None
        self._last_countdown_second = None

    async def broadcast_game_state(self):
        await self._broadcast(self.session.game_state_message())

    async def _maybe_apply_ratings(self, reason: str = 'game_over'):
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
        for connection, account in list(self._accounts.items()):
            if account.username in ratings:
                self._accounts[connection] = UserAccount(
                    account.username,
                    ratings[account.username],
                )
        self._ratings_applied = True
        await self._broadcast(
            RatingUpdate(
                winner=winner.username,
                loser=loser.username,
                ratings=ratings,
                reason=reason,
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
        try:
            await websocket.send(encode_message(message_to_dict(message)))
        except ConnectionClosed:
            pass

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
