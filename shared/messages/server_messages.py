from typing import Any, Dict, List, Optional

from shared.messages.types import ServerMessageType


class PlayerInfo:
    def __init__(self, username: str, color: str, rating: int):
        self.username = username
        self.color = color
        self.rating = rating

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'color': self.color,
            'rating': self.rating,
        }


class JoinAccepted:
    """Authentication succeeded; player is logged in but not yet matched."""

    TYPE = ServerMessageType.JOIN_ACCEPTED

    def __init__(self, username: str, rating: int):
        self.username = username
        self.rating = rating

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
            'rating': self.rating,
        }


class QueueStatus:
    TYPE = ServerMessageType.QUEUE_STATUS

    def __init__(self, timeout_seconds: int, elo_range: int):
        self.timeout_seconds = timeout_seconds
        self.elo_range = elo_range

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'timeout_seconds': self.timeout_seconds,
            'elo_range': self.elo_range,
            'message': 'searching for opponent',
        }


class MatchFound:
    TYPE = ServerMessageType.MATCH_FOUND

    def __init__(
        self,
        username: str,
        color: str,
        rating: int,
        players: List[PlayerInfo],
        room_id: Optional[str] = None,
    ):
        self.username = username
        self.color = color
        self.rating = rating
        self.players = players
        self.room_id = room_id

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'type': self.TYPE,
            'username': self.username,
            'color': self.color,
            'rating': self.rating,
            'players': [player.to_dict() for player in self.players],
        }
        if self.room_id is not None:
            payload['room_id'] = self.room_id
        return payload


class NoMatch:
    TYPE = ServerMessageType.NO_MATCH

    def __init__(self, message: str = 'no player found'):
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'message': self.message,
        }


class RoomCreated:
    TYPE = ServerMessageType.ROOM_CREATED

    def __init__(
        self,
        room_id: str,
        username: str,
        role: str,
        rating: int,
        members: List[PlayerInfo],
    ):
        self.room_id = room_id
        self.username = username
        self.role = role
        self.rating = rating
        self.members = members

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'room_id': self.room_id,
            'username': self.username,
            'role': self.role,
            'rating': self.rating,
            'members': [member.to_dict() for member in self.members],
        }


class RoomJoined:
    TYPE = ServerMessageType.ROOM_JOINED

    def __init__(
        self,
        room_id: str,
        username: str,
        role: str,
        rating: int,
        members: List[PlayerInfo],
        game_started: bool,
    ):
        self.room_id = room_id
        self.username = username
        self.role = role
        self.rating = rating
        self.members = members
        self.game_started = game_started

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'room_id': self.room_id,
            'username': self.username,
            'role': self.role,
            'rating': self.rating,
            'members': [member.to_dict() for member in self.members],
            'game_started': self.game_started,
        }


class DisconnectCountdown:
    TYPE = ServerMessageType.DISCONNECT_COUNTDOWN

    def __init__(
        self,
        username: str,
        seconds_remaining: int,
        total_seconds: int,
    ):
        self.username = username
        self.seconds_remaining = seconds_remaining
        self.total_seconds = total_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
            'seconds_remaining': self.seconds_remaining,
            'total_seconds': self.total_seconds,
        }


class RatingUpdate:
    TYPE = ServerMessageType.RATING_UPDATE

    def __init__(
        self,
        winner: str,
        loser: str,
        ratings: Dict[str, int],
        reason: str = 'game_over',
    ):
        self.winner = winner
        self.loser = loser
        self.ratings = ratings
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'winner': self.winner,
            'loser': self.loser,
            'ratings': self.ratings,
            'reason': self.reason,
        }


class ErrorMessage:
    TYPE = ServerMessageType.ERROR

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'code': self.code,
            'message': self.message,
        }
