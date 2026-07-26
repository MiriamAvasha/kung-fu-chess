from typing import Any, Dict


class JoinRequest:
    TYPE = 'join'

    def __init__(self, username: str):
        self.username = username

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'username': self.username,
        }


class MoveRequest:
    TYPE = 'move'

    def __init__(self, command: str):
        self.command = command

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.TYPE,
            'command': self.command,
        }
