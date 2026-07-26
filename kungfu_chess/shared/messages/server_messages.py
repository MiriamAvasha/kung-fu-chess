from typing import Any, Dict, List

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
    ):
        self.username = username
        self.color = color
        self.rating = rating
        self.players = players

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
            'color': self.color,
            'rating': self.rating,
            'players': [player.to_dict() for player in self.players],
        }


class NoMatch:
    TYPE = ServerMessageType.NO_MATCH

    def __init__(self, message: str = 'no player found'):
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'message': self.message,
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
