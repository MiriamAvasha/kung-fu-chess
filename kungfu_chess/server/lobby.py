from typing import Any, Dict, List, Optional

from shared.messages.server_messages import PlayerInfo
from shared.username import validate_username


COLOR_WHITE = 'w'
COLOR_BLACK = 'b'
MAX_PLAYERS = 2


class LobbyError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Player:
    def __init__(
        self,
        username: str,
        color: str,
        rating: int,
        connection: Any,
    ):
        self.username = username
        self.color = color
        self.rating = rating
        self.connection = connection

    def to_info(self) -> PlayerInfo:
        return PlayerInfo(self.username, self.color, self.rating)


class Lobby:
    def __init__(self):
        self._players_by_connection: Dict[Any, Player] = {}
        self._seat_white: Optional[Player] = None
        self._seat_black: Optional[Player] = None

    @property
    def players(self) -> List[Player]:
        seated = []
        if self._seat_white is not None:
            seated.append(self._seat_white)
        if self._seat_black is not None:
            seated.append(self._seat_black)
        return seated

    def is_full(self) -> bool:
        return len(self.players) >= MAX_PLAYERS

    def is_ready(self) -> bool:
        return (
            self._seat_white is not None
            and self._seat_black is not None
        )

    def get_player(self, connection: Any) -> Optional[Player]:
        return self._players_by_connection.get(connection)

    def get_by_color(self, color: str) -> Optional[Player]:
        if color == COLOR_WHITE:
            return self._seat_white
        if color == COLOR_BLACK:
            return self._seat_black
        return None

    def player_infos(self) -> List[PlayerInfo]:
        return [player.to_info() for player in self.players]

    def try_join(
        self,
        username: str,
        rating: int,
        connection: Any,
    ) -> Player:
        if connection in self._players_by_connection:
            raise LobbyError(
                'already_joined',
                'this connection already joined the lobby',
            )

        ok, result = validate_username(username)
        if not ok:
            raise LobbyError('invalid_username', result)

        normalized = result
        for player in self.players:
            if player.username.lower() == normalized.lower():
                raise LobbyError(
                    'username_taken',
                    'username is already taken',
                )

        if self.is_full():
            raise LobbyError('room_full', 'lobby supports only 2 players')

        if self._seat_white is None:
            color = COLOR_WHITE
        else:
            color = COLOR_BLACK

        player = Player(normalized, color, rating, connection)
        if color == COLOR_WHITE:
            self._seat_white = player
        else:
            self._seat_black = player
        self._players_by_connection[connection] = player
        return player

    def update_ratings(self, ratings: Dict[str, int]) -> None:
        for player in self.players:
            if player.username in ratings:
                player.rating = ratings[player.username]

    def leave(self, connection: Any) -> Optional[Player]:
        player = self._players_by_connection.pop(connection, None)
        if player is None:
            return None
        if self._seat_white is player:
            self._seat_white = None
        if self._seat_black is player:
            self._seat_black = None
        return player
