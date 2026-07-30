from typing import Any, Awaitable, Callable, Dict, Optional, Set, Type

from websockets.exceptions import ConnectionClosed

from server.auth import AuthService, UserAccount
from server.auth.store_factory import open_user_store
from server.matchmaking import Matchmaker
from server.rating import RatingService
from server.rooms import Room, RoomManager
from server.websocket.config import AUTO_RESIGN_SECONDS
from server.websocket.handlers import (
    AuthHandlers,
    DisconnectHandler,
    MatchmakingHandlers,
    MoveHandlers,
    RoomHandlers,
)
from server.websocket.ratings import RatingCoordinator
from server.websocket.ticker import RoomTicker
from server.websocket.transport import WebSocketTransport
from shared.activity_log import setup_activity_logger
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
from shared.messages.errors import ProtocolError
from shared.messages.parsers import parse_client_message
from shared.messages.server_messages import ErrorMessage
from shared.protocol import error_message


ClientHandler = Callable[[Any, Any], Awaitable[None]]


class GameServer:
    """Application coordinator for WebSocket transport and game services."""

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
        self.accounts: Dict[Any, UserAccount] = {}
        self.auto_resign_seconds = auto_resign_seconds

        self._accounts = self.accounts
        self._auto_resign_seconds = self.auto_resign_seconds

        self._logger = logger or setup_activity_logger(
            'kungfu.server',
            'server.log',
            console=True,
        )
        self.transport = WebSocketTransport(self.clients, self._logger)

        if auth_service is not None and rating_service is not None:
            self.auth_service = auth_service
            self.rating_service = rating_service
            self._db_connection = None
        else:
            repository, self._db_connection = open_user_store(db_path)
            self.auth_service = auth_service or AuthService(repository)
            self.rating_service = (
                rating_service or RatingService(repository)
            )

        self._auth_service = self.auth_service
        self._rating_service = self.rating_service

        self.auth_handlers = AuthHandlers(self)
        self.matchmaking_handlers = MatchmakingHandlers(self)
        self.room_handlers = RoomHandlers(self)
        self.move_handlers = MoveHandlers(self)
        self.disconnect_handler = DisconnectHandler(self)
        self.rating_coordinator = RatingCoordinator(self)
        self.ticker = RoomTicker(self)

        self._client_handlers: Dict[Type, ClientHandler] = {
            JoinRequest: self.auth_handlers.handle_join,
            PlayRequest: self.matchmaking_handlers.handle_play,
            CreateRoomRequest: self.room_handlers.handle_create_room,
            JoinRoomRequest: self.room_handlers.handle_join_room,
            MoveRequest: self.move_handlers.handle_move,
        }

    async def handle_client(self, websocket: Any) -> None:
        self.clients.add(websocket)
        self.log('IN', 'client_connected')
        try:
            async for raw_message in websocket:
                if not isinstance(raw_message, str):
                    await self.send(
                        websocket,
                        error_message(
                            'invalid_command',
                            'message must be text JSON',
                        ),
                    )
                    continue

                self.log('IN', raw_message)
                try:
                    message = parse_client_message(raw_message)
                except ProtocolError as error:
                    await self.send(
                        websocket,
                        ErrorMessage('invalid_command', str(error)),
                    )
                    continue

                handler = self._client_handlers.get(type(message))
                if handler is None:
                    await self.send(
                        websocket,
                        ErrorMessage(
                            'invalid_command',
                            'unsupported message type',
                        ),
                    )
                    continue
                await handler(websocket, message)
        except ConnectionClosed:
            pass
        finally:
            await self.disconnect_handler.handle(websocket)
            self.clients.discard(websocket)
            self.log('IN', 'client_disconnected')

    def require_account(self, websocket: Any) -> Optional[UserAccount]:
        return self.accounts.get(websocket)

    def refresh_account(
        self,
        websocket: Any,
        account: UserAccount,
    ) -> UserAccount:
        fresh = self.auth_service.get_account(account.username)
        if fresh is not None:
            self.accounts[websocket] = fresh
            return fresh
        return account

    async def run_ticker(self) -> None:
        await self.ticker.run()

    async def broadcast_game_state(self, room: Room) -> None:
        await self.broadcast_room(
            room,
            room.session.game_state_message(),
        )

    async def maybe_apply_ratings(
        self,
        room: Room,
        reason: str = 'game_over',
    ) -> None:
        await self.rating_coordinator.maybe_apply(room, reason)

    async def _maybe_apply_ratings(
        self,
        room: Room,
        reason: str = 'game_over',
    ) -> None:
        await self.maybe_apply_ratings(room, reason)

    async def send(self, websocket: Any, message: Any) -> None:
        await self.transport.send(websocket, message)

    async def _send(self, websocket: Any, message: Any) -> None:
        await self.send(websocket, message)

    async def broadcast_room(self, room: Room, message: Any) -> None:
        await self.transport.broadcast_room(room, message)

    async def _broadcast_room(self, room: Room, message: Any) -> None:
        await self.broadcast_room(room, message)

    def log(self, direction: str, payload: str) -> None:
        self.transport.log(direction, payload)

    def _log(self, direction: str, payload: str) -> None:
        self.log(direction, payload)

    def close(self) -> None:
        if self._db_connection is not None:
            self._db_connection.close()
            self._db_connection = None
