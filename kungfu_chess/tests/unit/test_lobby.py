import pytest

from server.lobby import Lobby, LobbyError
from shared.messages.client_messages import JoinRequest, MoveRequest
from shared.messages.errors import ProtocolError
from shared.messages.parsers import parse_client_message, parse_server_message
from shared.messages.server_messages import ErrorMessage, JoinAccepted, PlayerInfo
from shared.protocol import encode_message
from shared.username import validate_username


@pytest.mark.parametrize(
    'raw, expected_ok',
    [
        ('Alice', True),
        ('bob_1', True),
        ('', False),
        ('   ', False),
        ('bad name', False),
        ('toolongusername123456', False),
        ('ok!', False),
    ],
)
def test_validate_username(raw, expected_ok):
    ok, _result = validate_username(raw)
    assert ok is expected_ok


def test_lobby_assigns_white_then_black():
    lobby = Lobby()
    first = lobby.try_join('Alice', connection='c1')
    second = lobby.try_join('Bob', connection='c2')

    assert first.color == 'w'
    assert second.color == 'b'
    assert lobby.is_ready() is True


def test_lobby_rejects_third_player():
    lobby = Lobby()
    lobby.try_join('Alice', connection='c1')
    lobby.try_join('Bob', connection='c2')

    with pytest.raises(LobbyError) as error:
        lobby.try_join('Carol', connection='c3')
    assert error.value.code == 'room_full'


def test_lobby_rejects_taken_username_and_already_joined():
    lobby = Lobby()
    lobby.try_join('Alice', connection='c1')

    with pytest.raises(LobbyError) as taken:
        lobby.try_join('alice', connection='c2')
    assert taken.value.code == 'username_taken'

    with pytest.raises(LobbyError) as joined:
        lobby.try_join('Bob', connection='c1')
    assert joined.value.code == 'already_joined'


def test_lobby_leave_frees_seat():
    lobby = Lobby()
    lobby.try_join('Alice', connection='c1')
    lobby.try_join('Bob', connection='c2')
    lobby.leave('c1')

    replacement = lobby.try_join('Carol', connection='c3')
    assert replacement.color == 'w'
    assert lobby.is_ready() is True


def test_join_and_move_message_roundtrip():
    join = JoinRequest('Alice')
    move = MoveRequest('WPe2e4')

    assert parse_client_message(encode_message(join.to_dict())).username == 'Alice'
    assert parse_client_message(encode_message(move.to_dict())).command == 'WPe2e4'


def test_parse_client_message_rejects_unknown_type():
    with pytest.raises(ProtocolError):
        parse_client_message('{"type":"jump"}')


def test_join_accepted_and_error_server_message_roundtrip():
    accepted = JoinAccepted(
        'Alice',
        'w',
        [PlayerInfo('Alice', 'w')],
    )
    parsed_accepted = parse_server_message(
        encode_message(accepted.to_dict())
    )
    assert parsed_accepted.username == 'Alice'
    assert parsed_accepted.color == 'w'
    assert parsed_accepted.players[0].username == 'Alice'

    error = ErrorMessage('room_full', 'lobby supports only 2 players')
    parsed_error = parse_server_message(encode_message(error.to_dict()))
    assert parsed_error.code == 'room_full'
    assert parsed_error.message == 'lobby supports only 2 players'
