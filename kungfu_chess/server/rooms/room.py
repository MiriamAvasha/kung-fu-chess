from typing import Any, Dict, List, Optional

from constants import PieceColor
from engine.game_factory import build_engine
from server.game_session import GameSession
from shared.messages.server_messages import PlayerInfo


class RoomRole:
    WHITE = PieceColor.WHITE.value
    BLACK = PieceColor.BLACK.value
    VIEWER = 'viewer'


class RoomError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class RoomMember:
    def __init__(
        self,
        username: str,
        role: str,
        rating: int,
        connection: Any,
    ):
        self.username = username
        self.role = role
        self.rating = rating
        self.connection = connection

    @property
    def is_player(self) -> bool:
        return self.role in (RoomRole.WHITE, RoomRole.BLACK)

    def to_info(self) -> PlayerInfo:
        return PlayerInfo(self.username, self.role, self.rating)


class Room:
    def __init__(self, room_id: str, rated: bool = False):
        self.room_id = room_id
        self.rated = rated
        self.session = GameSession(build_engine())
        self._members: Dict[Any, RoomMember] = {}
        self._seat_white: Optional[RoomMember] = None
        self._seat_black: Optional[RoomMember] = None
        self._viewers: List[RoomMember] = []
        self.game_started = False
        self.ratings_applied = False
        self.disconnect_deadline: Optional[float] = None
        self.disconnect_player: Optional[RoomMember] = None
        self.last_countdown_second: Optional[int] = None

    @property
    def players(self) -> List[RoomMember]:
        seated = []
        if self._seat_white is not None:
            seated.append(self._seat_white)
        if self._seat_black is not None:
            seated.append(self._seat_black)
        return seated

    @property
    def members(self) -> List[RoomMember]:
        return list(self._members.values())

    @property
    def connections(self):
        return tuple(self._members.keys())

    def is_ready(self) -> bool:
        return self._seat_white is not None and self._seat_black is not None

    def get_member(self, connection: Any) -> Optional[RoomMember]:
        return self._members.get(connection)

    def get_by_color(self, color: str) -> Optional[RoomMember]:
        if color == RoomRole.WHITE:
            return self._seat_white
        if color == RoomRole.BLACK:
            return self._seat_black
        return None

    def player_infos(self) -> List[PlayerInfo]:
        return [member.to_info() for member in self.players]

    def member_infos(self) -> List[PlayerInfo]:
        return [member.to_info() for member in self.members]

    def add_creator(
        self,
        username: str,
        rating: int,
        connection: Any,
    ) -> RoomMember:
        if self._seat_white is not None:
            raise RoomError('room_full', 'room already has a creator')
        member = RoomMember(username, RoomRole.WHITE, rating, connection)
        self._seat_white = member
        self._members[connection] = member
        return member

    def join(
        self,
        username: str,
        rating: int,
        connection: Any,
    ) -> RoomMember:
        if connection in self._members:
            raise RoomError('already_in_room', 'already in this room')

        if self._seat_black is None:
            member = RoomMember(username, RoomRole.BLACK, rating, connection)
            self._seat_black = member
            self._members[connection] = member
            return member

        member = RoomMember(username, RoomRole.VIEWER, rating, connection)
        self._viewers.append(member)
        self._members[connection] = member
        return member

    def seat_match(
        self,
        white_username: str,
        white_rating: int,
        white_connection: Any,
        black_username: str,
        black_rating: int,
        black_connection: Any,
    ) -> None:
        self.clear_members()
        white = RoomMember(
            white_username,
            RoomRole.WHITE,
            white_rating,
            white_connection,
        )
        black = RoomMember(
            black_username,
            RoomRole.BLACK,
            black_rating,
            black_connection,
        )
        self._seat_white = white
        self._seat_black = black
        self._members[white_connection] = white
        self._members[black_connection] = black
        self.game_started = True
        self.ratings_applied = False
        self.clear_disconnect_timer()

    def update_ratings(self, ratings: Dict[str, int]) -> None:
        for member in self.members:
            if member.username in ratings:
                member.rating = ratings[member.username]

    def leave(self, connection: Any) -> Optional[RoomMember]:
        member = self._members.pop(connection, None)
        if member is None:
            return None
        if self._seat_white is member:
            self._seat_white = None
        if self._seat_black is member:
            self._seat_black = None
        if member in self._viewers:
            self._viewers.remove(member)
        return member

    def clear_members(self) -> None:
        self._members.clear()
        self._seat_white = None
        self._seat_black = None
        self._viewers.clear()

    def clear_disconnect_timer(self) -> None:
        self.disconnect_deadline = None
        self.disconnect_player = None
        self.last_countdown_second = None

    def is_empty(self) -> bool:
        return not self._members
