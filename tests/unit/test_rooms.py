import pytest

from constants import PieceColor
from server.rooms import RoomError, RoomManager, RoomRole


def test_create_room_seats_creator_as_white():
    manager = RoomManager()
    room = manager.create_room(rated=False)
    member = room.add_creator('Alice', 1200, 'c1')
    manager.register_connection('c1', room)

    assert member.role == RoomRole.WHITE
    assert room.get_by_color(PieceColor.WHITE.value).username == 'Alice'
    assert manager.get(room.room_id) is room
    assert manager.get_by_connection('c1') is room


def test_second_joiner_is_black_others_are_viewers():
    manager = RoomManager()
    room = manager.create_room()
    room.add_creator('Alice', 1200, 'c1')
    manager.register_connection('c1', room)

    black = room.join('Bob', 1250, 'c2')
    manager.register_connection('c2', room)
    viewer = room.join('Carol', 1100, 'c3')
    manager.register_connection('c3', room)

    assert black.role == RoomRole.BLACK
    assert viewer.role == RoomRole.VIEWER
    assert room.is_ready() is True
    assert len(room.members) == 3


def test_room_ids_are_unique_and_case_insensitive_lookup():
    manager = RoomManager()
    room = manager.create_room()
    assert manager.get(room.room_id.lower()) is room
    assert manager.get(room.room_id.upper()) is room


def test_leave_removes_empty_room():
    manager = RoomManager()
    room = manager.create_room()
    room.add_creator('Alice', 1200, 'c1')
    manager.register_connection('c1', room)
    room_id = room.room_id

    manager.leave('c1')
    assert manager.get(room_id) is None


def test_cannot_register_connection_in_two_rooms():
    manager = RoomManager()
    first = manager.create_room()
    second = manager.create_room()
    first.add_creator('Alice', 1200, 'c1')
    manager.register_connection('c1', first)

    second.add_creator('Bob', 1200, 'c2')
    manager.register_connection('c2', second)
    with pytest.raises(RoomError) as error:
        manager.register_connection('c1', second)
    assert error.value.code == 'already_in_room'


def test_rated_flag_defaults_false():
    room = RoomManager().create_room()
    assert room.rated is False
    rated = RoomManager().create_room(rated=True)
    assert rated.rated is True
