from typing import Any, Dict

from shared.messages.types import ClientMessageType


class JoinRequest:
    TYPE = ClientMessageType.JOIN

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
            'password': self.password,
        }


class PlayRequest:
    TYPE = ClientMessageType.PLAY

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
        }


class CreateRoomRequest:
    TYPE = ClientMessageType.CREATE_ROOM

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
        }


class JoinRoomRequest:
    TYPE = ClientMessageType.JOIN_ROOM

    def __init__(self, room_id: str):
        self.room_id = room_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'room_id': self.room_id,
        }


class MoveRequest:
    TYPE = ClientMessageType.MOVE

    def __init__(self, command: str):
        self.command = command

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'command': self.command,
        }
