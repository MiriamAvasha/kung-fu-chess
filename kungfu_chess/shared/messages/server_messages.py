from typing import Any, Dict, List


class PlayerInfo:
    def __init__(self, username: str, color: str):
        self.username = username
        self.color = color

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'color': self.color,
        }


class JoinAccepted:
    TYPE = 'join_accepted'

    def __init__(
        self,
        username: str,
        color: str,
        players: List[PlayerInfo],
    ):
        self.username = username
        self.color = color
        self.players = players

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
            'color': self.color,
            'players': [player.to_dict() for player in self.players],
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
