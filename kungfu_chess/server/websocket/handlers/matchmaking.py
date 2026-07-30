from typing import TYPE_CHECKING, Any

from constants import PieceColor, color_display_name
from server.matchmaking import (
    ELO_RANGE,
    SEARCH_TIMEOUT_SECONDS,
    QueueEntry,
)
from shared.messages.client_messages import PlayRequest
from shared.messages.server_messages import (
    ErrorMessage,
    MatchFound,
    QueueStatus,
)

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class MatchmakingHandlers:
    def __init__(self, server: 'GameServer'):
        self.server = server

    async def handle_play(
        self,
        websocket: Any,
        message: PlayRequest,
    ) -> None:
        account = self.server.require_account(websocket)
        if account is None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before pressing Play',
                ),
            )
            return

        if self.server.rooms.get_by_connection(websocket) is not None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'already_in_game',
                    'already seated in a room',
                ),
            )
            return

        account = self.server.refresh_account(websocket, account)
        entry = QueueEntry(account.username, account.rating, websocket)
        try:
            matched = self.server.matchmaker.enqueue(entry)
        except ValueError:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'already_searching',
                    'already searching for a match',
                ),
            )
            return

        if matched is None:
            await self.server.send(
                websocket,
                QueueStatus(
                    timeout_seconds=SEARCH_TIMEOUT_SECONDS,
                    elo_range=ELO_RANGE,
                ),
            )
            return

        white_entry, black_entry = matched
        await self.start_rated_match(white_entry, black_entry)

    async def start_rated_match(
        self,
        white_entry: QueueEntry,
        black_entry: QueueEntry,
    ) -> None:
        room = self.server.rooms.create_room(rated=True)
        room.seat_match(
            white_entry.username,
            white_entry.rating,
            white_entry.connection,
            black_entry.username,
            black_entry.rating,
            black_entry.connection,
        )
        self.server.rooms.register_connection(
            white_entry.connection,
            room,
        )
        self.server.rooms.register_connection(
            black_entry.connection,
            room,
        )

        players = room.player_infos()
        for player in room.players:
            await self.server.send(
                player.connection,
                MatchFound(
                    username=player.username,
                    color=player.role,
                    rating=player.rating,
                    players=players,
                    room_id=room.room_id,
                ),
            )
            await self.server.send(
                player.connection,
                room.session.initial_message(),
            )

        self.server.log(
            'SYS',
            'Rated match in {}: {} ({}) vs {} ({})'.format(
                room.room_id,
                white_entry.username,
                color_display_name(PieceColor.WHITE.value),
                black_entry.username,
                color_display_name(PieceColor.BLACK.value),
            ),
        )
