from typing import TYPE_CHECKING, Any

from server.rooms import RoomError, RoomRole
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRoomRequest,
)
from shared.messages.server_messages import (
    ErrorMessage,
    RoomCreated,
    RoomJoined,
)

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class RoomHandlers:
    def __init__(self, server: 'GameServer'):
        self.server = server

    async def handle_create_room(
        self,
        websocket: Any,
        message: CreateRoomRequest,
    ) -> None:
        account = self.server.require_account(websocket)
        if account is None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before creating a room',
                ),
            )
            return

        if self.server.rooms.get_by_connection(websocket) is not None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'already_in_room',
                    'already in a room',
                ),
            )
            return

        self.server.matchmaker.remove(websocket)
        account = self.server.refresh_account(websocket, account)

        try:
            room = self.server.rooms.create_room(rated=False)
            member = room.add_creator(
                account.username,
                account.rating,
                websocket,
            )
            self.server.rooms.register_connection(websocket, room)
        except RoomError as error:
            await self.server.send(
                websocket,
                ErrorMessage(error.code, error.message),
            )
            return

        await self.server.send(
            websocket,
            RoomCreated(
                room_id=room.room_id,
                username=member.username,
                role=member.role,
                rating=member.rating,
                members=room.member_infos(),
            ),
        )
        self.server.log(
            'SYS',
            'Room {} created by {}'.format(
                room.room_id,
                account.username,
            ),
        )

    async def handle_join_room(
        self,
        websocket: Any,
        message: JoinRoomRequest,
    ) -> None:
        account = self.server.require_account(websocket)
        if account is None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'login before joining a room',
                ),
            )
            return

        if self.server.rooms.get_by_connection(websocket) is not None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'already_in_room',
                    'already in a room',
                ),
            )
            return

        room = self.server.rooms.get(message.room_id)
        if room is None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'room_not_found',
                    'room {} not found'.format(message.room_id),
                ),
            )
            return

        self.server.matchmaker.remove(websocket)
        account = self.server.refresh_account(websocket, account)

        try:
            member = room.join(
                account.username,
                account.rating,
                websocket,
            )
            self.server.rooms.register_connection(websocket, room)
        except RoomError as error:
            await self.server.send(
                websocket,
                ErrorMessage(error.code, error.message),
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
            await self.server.send(
                occupant.connection,
                RoomJoined(
                    room_id=room.room_id,
                    username=occupant.username,
                    role=occupant.role,
                    rating=occupant.rating,
                    members=members,
                    game_started=room.game_started,
                ),
            )

        if just_became_ready:
            await self.server.broadcast_room(
                room,
                room.session.initial_message(),
            )
            white = room.get_by_color(RoomRole.WHITE)
            black = room.get_by_color(RoomRole.BLACK)
            self.server.log(
                'SYS',
                'Casual room {} started: {} vs {}'.format(
                    room.room_id,
                    white.username,
                    black.username,
                ),
            )
        elif room.game_started and member.role == RoomRole.VIEWER:
            await self.server.send(
                websocket,
                room.session.game_state_message(),
            )

        self.server.log(
            'SYS',
            '{} joined room {} as {}'.format(
                account.username,
                room.room_id,
                member.role,
            ),
        )
