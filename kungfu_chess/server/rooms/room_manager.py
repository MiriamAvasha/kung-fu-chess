import secrets
from typing import Any, Dict, List, Optional

from server.rooms.room import Room, RoomError


def generate_room_id(length: int = 6) -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class RoomManager:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._by_connection: Dict[Any, str] = {}

    def rooms(self) -> List[Room]:
        return list(self._rooms.values())

    def get(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id.upper())

    def get_by_connection(self, connection: Any) -> Optional[Room]:
        room_id = self._by_connection.get(connection)
        if room_id is None:
            return None
        return self._rooms.get(room_id)

    def create_room(self, rated: bool = False) -> Room:
        for _ in range(20):
            room_id = generate_room_id()
            if room_id not in self._rooms:
                room = Room(room_id, rated=rated)
                self._rooms[room_id] = room
                return room
        raise RoomError('room_create_failed', 'could not allocate room id')

    def register_connection(self, connection: Any, room: Room) -> None:
        existing = self._by_connection.get(connection)
        if existing is not None and existing != room.room_id:
            raise RoomError('already_in_room', 'already in another room')
        self._by_connection[connection] = room.room_id

    def leave(self, connection: Any) -> Optional[Room]:
        room_id = self._by_connection.pop(connection, None)
        if room_id is None:
            return None
        room = self._rooms.get(room_id)
        if room is None:
            return None
        room.leave(connection)
        if room.is_empty():
            self._rooms.pop(room_id, None)
        return room

    def remove_room(self, room_id: str) -> None:
        room = self._rooms.pop(room_id.upper(), None)
        if room is None:
            return
        for connection in list(room.connections):
            self._by_connection.pop(connection, None)
        room.clear_members()
