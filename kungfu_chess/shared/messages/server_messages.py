from typing import Any, Dict, List


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
    TYPE = 'join_accepted'

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


class RatingUpdate:
    TYPE = 'rating_update'

    def __init__(
        self,
        winner: str,
        loser: str,
        ratings: Dict[str, int],
    ):
        self.winner = winner
        self.loser = loser
        self.ratings = ratings

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'winner': self.winner,
            'loser': self.loser,
            'ratings': self.ratings,
        }


class ErrorMessage:
    TYPE = 'error'

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'code': self.code,
            'message': self.message,
        }
