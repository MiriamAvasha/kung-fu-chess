import asyncio
import contextlib
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Set, Type

import websockets
from websockets.exceptions import ConnectionClosed

from constants import PieceColor, color_display_name, opponent_color
from server.auth import AuthError, AuthService, UserAccount, UserRepository
from server.db import open_database
from server.matchmaking import (
    ELO_RANGE,
    SEARCH_TIMEOUT_SECONDS,
    Matchmaker,
    QueueEntry,
)
from server.rating import RatingService
from server.rooms import Room, RoomError, RoomManager, RoomRole
from shared.activity_log import log_activity, setup_activity_logger
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
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
    RoomCreated,
    RoomJoined,
)
from shared.protocol import encode_message, error_message


HOST = 'localhost'
PORT = 8765
TICK_SECONDS = 0.05
AUTO_RESIGN_SECONDS = 20

ClientHandler = Callable[[Any, Any], Awaitable[None]]


class GameServer:
    def __init__(
        self,
        auth_service: Optional[AuthService] = None,
        rating_service: Optional[RatingService] = None,
        matchmaker: Optional[Matchmaker] = None,
        room_manager: Optional[RoomManager] = None,
        db_path=None,
        auto_resign_seconds: int = AUTO_RESIGN_SECONDS,
        logger=None,
    ):
        self.rooms = room_manager or RoomManager()
        self.matchmaker = matchmaker or Matchmaker()
        self.clients: Set[Any] = set()
        self._accounts: Dict[Any, UserAccount] = {}
        self._auto_resign_seconds = auto_resign_seconds
        self._logger = logger or setup_activity_logger(
            'kungfu.server',
            'server.log',
            console=True,
        )

        if auth_service is not None and rating_service is not None:
            self._auth_service = auth_service
            self._rating_service = rating_service
            self._db_connection = None
        else:
            self._db_connection = open_database(db_path)
            repository = UserRepository(self._db_connection)
            self._auth_service = auth_service or AuthService(repository)
            self._rating_service = rating_service or RatingService(repository)

        self._client_handlers: Dict[Type, ClientHandler] = {
            JoinRequest: self._handle_join,
            PlayRequest: self._handle_play,
            CreateRoomRequest: self._handle_create_room,
            JoinRoomRequest: self._handle_join_room,
            MoveRequest: self._handle_move,
        }

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        self._log('IN', 'client_connected')
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

                self._log('IN', raw_message)
                try:
                    message = parse_client_message(raw_message)
                except ProtocolError as error:
                    await self._send(
                        websocket,
                        ErrorMessage('invalid_command', str(error)).to_dict(),
                    )
                    continue

                handler = self._client_handlers.get(type(message))
                if handler is None:
                    await self._send(
                        websocket,
                        ErrorMessage(
                            'invalid_command',
                            'unsupported message type',
                        ).to_dict(),
                    )
                    continue
                await handler(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            await self._handle_disconnect(websocket)
            self.clients.discard(websocket)
            self._log('IN', 'client_disconnected')

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
        self._log(
            'SYS',
            'Player logged in: {} (rating {})'.format(
                account.username,
                account.rating,
            ),
        )

    def _require_account(self, websocket):
        return self._accounts.get(websocket)

    def _refresh_account(self, websocket, account: UserAccount) -> UserAccount:
        fresh = self._auth_service.get_account(account.username)
        if fresh is not None:
            self._accounts[websocket] = fresh
            return fresh
        return account

    async def _handle_play(self, websocket, message: PlayRequest):
        account = self._require_account(websocket)
        if account is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before pressing Play',
                ).to_dict(),
            )
            return

        if self.rooms.get_by_connection(websocket) is not None:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_in_game',
                    'already seated in a room',
                ).to_dict(),
            )
            return

        account = self._refresh_account(websocket, account)
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
        await self._start_rated_match(white_entry, black_entry)

    async def _start_rated_match(
        self,
        white_entry: QueueEntry,
        black_entry: QueueEntry,
    ):
        room = self.rooms.create_room(rated=True)
        room.seat_match(
            white_entry.username,
            white_entry.rating,
            white_entry.connection,
            black_entry.username,
            black_entry.rating,
            black_entry.connection,
        )
        self.rooms.register_connection(white_entry.connection, room)
        self.rooms.register_connection(black_entry.connection, room)

        players = room.player_infos()
        for player in room.players:
            await self._send(
                player.connection,
                MatchFound(
                    username=player.username,
                    color=player.role,
                    rating=player.rating,
                    players=players,
                    room_id=room.room_id,
                ).to_dict(),
            )
            await self._send(player.connection, room.session.initial_message())

        self._log(
            'SYS',
            'Rated match in {}: {} ({}) vs {} ({})'.format(
                room.room_id,
                white_entry.username,
                color_display_name(PieceColor.WHITE.value),
                black_entry.username,
                color_display_name(PieceColor.BLACK.value),
            ),
        )

    async def _handle_create_room(self, websocket, message: CreateRoomRequest):
        account = self._require_account(websocket)
        if account is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before creating a room',
                ).to_dict(),
            )
            return

        if self.rooms.get_by_connection(websocket) is not None:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_in_room',
                    'already in a room',
                ).to_dict(),
            )
            return

        self.matchmaker.remove(websocket)
        account = self._refresh_account(websocket, account)

        try:
            room = self.rooms.create_room(rated=False)
            member = room.add_creator(
                account.username,
                account.rating,
                websocket,
            )
            self.rooms.register_connection(websocket, room)
        except RoomError as error:
            await self._send(
                websocket,
                ErrorMessage(error.code, error.message).to_dict(),
            )
            return

        await self._send(
            websocket,
            RoomCreated(
                room_id=room.room_id,
                username=member.username,
                role=member.role,
                rating=member.rating,
                members=room.member_infos(),
            ).to_dict(),
        )
        self._log(
            'SYS',
            'Room {} created by {}'.format(room.room_id, account.username),
        )

    async def _handle_join_room(self, websocket, message: JoinRoomRequest):
        account = self._require_account(websocket)
        if account is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before joining a room',
                ).to_dict(),
            )
            return

        if self.rooms.get_by_connection(websocket) is not None:
            await self._send(
                websocket,
                ErrorMessage(
                    'already_in_room',
                    'already in a room',
                ).to_dict(),
            )
            return

        room = self.rooms.get(message.room_id)
        if room is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'room_not_found',
                    'room {} not found'.format(message.room_id),
                ).to_dict(),
            )
            return

        self.matchmaker.remove(websocket)
        account = self._refresh_account(websocket, account)

        try:
            member = room.join(account.username, account.rating, websocket)
            self.rooms.register_connection(websocket, room)
        except RoomError as error:
            await self._send(
                websocket,
                ErrorMessage(error.code, error.message).to_dict(),
            )
            return

        just_became_ready = (
            member.role == RoomRole.BLACK
            and room.is_ready()
            and not room.game_started
        )
        if just_became_ready:
            room.game_started = True
            room.ratings_applied = False
            room.clear_disconnect_timer()

        members = room.member_infos()
        for occupant in room.members:
            await self._send(
                occupant.connection,
                RoomJoined(
                    room_id=room.room_id,
                    username=occupant.username,
                    role=occupant.role,
                    rating=occupant.rating,
                    members=members,
                    game_started=room.game_started,
                ).to_dict(),
            )

        if just_became_ready:
            await self._broadcast_room(room, room.session.initial_message())
            self._log(
                'SYS',
                'Casual room {} started: {} vs {}'.format(
                    room.room_id,
                    room.get_by_color(RoomRole.WHITE).username,
                    room.get_by_color(RoomRole.BLACK).username,
                ),
            )
        elif room.game_started and member.role == RoomRole.VIEWER:
            await self._send(websocket, room.session.game_state_message())

        self._log(
            'SYS',
            '{} joined room {} as {}'.format(
                account.username,
                room.room_id,
                member.role,
            ),
        )

    async def _handle_move(self, websocket, message: MoveRequest):
        room = self.rooms.get_by_connection(websocket)
        if room is None:
            await self._send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'join a room before sending moves',
                ).to_dict(),
            )
            return

        member = room.get_member(websocket)
        if member is None or not member.is_player:
            await self._send(
                websocket,
                ErrorMessage(
                    'viewer_cannot_move',
                    'viewers cannot send moves',
                ).to_dict(),
            )
            return

        if not room.is_ready() or not room.game_started:
            await self._send(
                websocket,
                ErrorMessage(
                    'game_not_ready',
                    'waiting for match to start',
                ).to_dict(),
            )
            return

        if room.session.is_game_over:
            await self._send(
                websocket,
                ErrorMessage('game_over', 'game already finished').to_dict(),
            )
            return

        result = room.session.handle_command(
            message.command,
            member.role,
        )
        await self._send(websocket, result)
        if (
            result.get('type') == 'move_result'
            and result.get('accepted')
        ):
            await self.broadcast_game_state(room)
            await self._maybe_apply_ratings(room)

    async def _handle_disconnect(self, websocket):
        self.matchmaker.remove(websocket)
        account = self._accounts.pop(websocket, None)
        room = self.rooms.get_by_connection(websocket)
        if room is None:
            if account is not None:
                self._log('SYS', 'Player left: {}'.format(account.username))
            return

        member = room.get_member(websocket)
        if (
            member is not None
            and member.is_player
            and room.game_started
            and not room.session.is_game_over
            and room.is_ready()
        ):
            room.disconnect_deadline = (
                time.monotonic() + self._auto_resign_seconds
            )
            room.disconnect_player = member
            room.last_countdown_second = None
            await self._broadcast_room(
                room,
                DisconnectCountdown(
                    username=member.username,
                    seconds_remaining=self._auto_resign_seconds,
                    total_seconds=self._auto_resign_seconds,
                ),
            )
            self._log(
                'SYS',
                'Player disconnected during game: {} — auto-resign in {}s'.format(
                    member.username,
                    self._auto_resign_seconds,
                ),
            )
            return

        self.rooms.leave(websocket)
        if account is not None:
            self._log('SYS', 'Player left: {}'.format(account.username))

    async def run_ticker(self):
        previous_by_room: Dict[str, float] = {}
        while True:
            await asyncio.sleep(TICK_SECONDS)
            now = time.monotonic()
            await self._expire_matchmaking(now)
            await self._tick_disconnect_countdowns(now)

            for room in list(self.rooms.rooms()):
                if not room.game_started or room.session.is_game_over:
                    previous_by_room.pop(room.room_id, None)
                    continue

                previous = previous_by_room.get(room.room_id, now)
                elapsed_ms = max(1, int((now - previous) * 1000))
                previous_by_room[room.room_id] = now
                if room.session.advance(elapsed_ms):
                    await self.broadcast_game_state(room)
                    await self._maybe_apply_ratings(room)

    async def _expire_matchmaking(self, now: float):
        expired = self.matchmaker.pop_expired(now)
        for entry in expired:
            await self._send(
                entry.connection,
                NoMatch('no player found').to_dict(),
            )
            self._log(
                'SYS',
                'Matchmaking timeout for {}'.format(entry.username),
            )

    async def _tick_disconnect_countdowns(self, now: float):
        for room in list(self.rooms.rooms()):
            if (
                room.disconnect_deadline is None
                or room.disconnect_player is None
                or room.session.is_game_over
            ):
                continue

            remaining = int(max(0, room.disconnect_deadline - now))
            if (
                room.last_countdown_second is None
                or remaining != room.last_countdown_second
            ):
                room.last_countdown_second = remaining
                await self._broadcast_room(
                    room,
                    DisconnectCountdown(
                        username=room.disconnect_player.username,
                        seconds_remaining=remaining,
                        total_seconds=self._auto_resign_seconds,
                    ),
                )

            if remaining > 0:
                continue

            loser = room.disconnect_player
            room.session.resign(loser.role)
            await self.broadcast_game_state(room)
            await self._maybe_apply_ratings(room, reason='auto_resign')
            room.clear_disconnect_timer()
            self._log('SYS', 'Auto-resign: {}'.format(loser.username))

    async def broadcast_game_state(self, room: Room):
        await self._broadcast_room(room, room.session.game_state_message())

    async def _maybe_apply_ratings(
        self,
        room: Room,
        reason: str = 'game_over',
    ):
        if room.ratings_applied or not room.session.is_game_over:
            return
        if not room.rated:
            room.ratings_applied = True
            return

        winner_color = room.session.winner_color()
        if winner_color is None:
            return

        winner = room.get_by_color(winner_color)
        loser = room.get_by_color(opponent_color(winner_color))
        if winner is None or loser is None:
            return

        ratings = self._rating_service.apply_match_result(
            winner.username,
            loser.username,
        )
        room.update_ratings(ratings)
        for connection, account in list(self._accounts.items()):
            if account.username in ratings:
                self._accounts[connection] = UserAccount(
                    account.username,
                    ratings[account.username],
                )
        room.ratings_applied = True
        await self._broadcast_room(
            room,
            RatingUpdate(
                winner=winner.username,
                loser=loser.username,
                ratings=ratings,
                reason=reason,
            ),
        )

    async def _broadcast_room(self, room: Room, message):
        encoded = encode_message(message_to_dict(message))
        self._log('OUT', encoded)
        disconnected = []
        for client in room.connections:
            try:
                await client.send(encoded)
            except ConnectionClosed:
                disconnected.append(client)
        for client in disconnected:
            self.clients.discard(client)

    async def _send(self, websocket, message):
        encoded = encode_message(message_to_dict(message))
        self._log('OUT', encoded)
        try:
            await websocket.send(encoded)
        except ConnectionClosed:
            pass

    def _log(self, direction: str, payload: str):
        log_activity(self._logger, direction, payload)

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
