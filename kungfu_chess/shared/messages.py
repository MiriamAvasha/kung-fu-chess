from typing import Any, Dict, List, Union

from shared.protocol import decode_message


class ProtocolError(ValueError):
    pass


class JoinRequest:
    TYPE = 'join'

    def __init__(self, username: str):
        self.username = username

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JoinRequest':
        username = data.get('username')
        if not isinstance(username, str):
            raise ProtocolError('join.username must be a string')
        return cls(username)


class PlayerInfo:
    def __init__(self, username: str, color: str):
        self.username = username
        self.color = color

    def to_dict(self) -> Dict[str, Any]:
        return {
            'username': self.username,
            'color': self.color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerInfo':
        if not isinstance(data, dict):
            raise ProtocolError('player must be an object')
        username = data.get('username')
        color = data.get('color')
        if not isinstance(username, str) or not isinstance(color, str):
            raise ProtocolError('player.username and player.color must be strings')
        return cls(username, color)


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JoinAccepted':
        username = data.get('username')
        color = data.get('color')
        players_raw = data.get('players')
        if not isinstance(username, str) or not isinstance(color, str):
            raise ProtocolError(
                'join_accepted.username and join_accepted.color must be strings'
            )
        if not isinstance(players_raw, list):
            raise ProtocolError('join_accepted.players must be a list')
        players = [PlayerInfo.from_dict(item) for item in players_raw]
        return cls(username, color, players)


class MoveRequest:
    TYPE = 'move'

    def __init__(self, command: str):
        self.command = command

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'command': self.command,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoveRequest':
        command = data.get('command')
        if not isinstance(command, str):
            raise ProtocolError('move.command must be a string')
        return cls(command)


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorMessage':
        code = data.get('code')
        message = data.get('message')
        if not isinstance(code, str) or not isinstance(message, str):
            raise ProtocolError('error.code and error.message must be strings')
        return cls(code, message)


ClientMessage = Union[JoinRequest, MoveRequest]


def parse_client_message(raw_message: str) -> ClientMessage:
    try:
        data = decode_message(raw_message)
    except (TypeError, ValueError) as error:
        raise ProtocolError('message must be a JSON object') from error

    message_type = data.get('type')
    if message_type == JoinRequest.TYPE:
        return JoinRequest.from_dict(data)
    if message_type == MoveRequest.TYPE:
        return MoveRequest.from_dict(data)
    raise ProtocolError(
        'unsupported message type: {}'.format(message_type)
    )


def message_to_dict(message: Any) -> Dict[str, Any]:
    if hasattr(message, 'to_dict'):
        return message.to_dict()
    if isinstance(message, dict):
        return message
    raise TypeError('unsupported message object')
