from typing import Any, Dict, List, Optional

from constants import PieceColor
from shared.messages.server_messages import PlayerInfo


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
        if color == PieceColor.WHITE.value:
            return self._seat_white
        if color == PieceColor.BLACK.value:
            return self._seat_black
        return None

    def player_infos(self) -> List[PlayerInfo]:
        return [player.to_info() for player in self.players]

    def seat_match(
        self,
        white_username: str,
        white_rating: int,
        white_connection: Any,
        black_username: str,
        black_rating: int,
        black_connection: Any,
    ) -> None:
        if self.is_ready():
            raise LobbyError('room_full', 'a match is already in progress')

        self.clear()
        white = Player(
            white_username,
            PieceColor.WHITE.value,
            white_rating,
            white_connection,
        )
        black = Player(
            black_username,
            PieceColor.BLACK.value,
            black_rating,
            black_connection,
        )
        self._seat_white = white
        self._seat_black = black
        self._players_by_connection[white_connection] = white
        self._players_by_connection[black_connection] = black

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

    def clear(self) -> None:
        self._players_by_connection.clear()
        self._seat_white = None
        self._seat_black = None
