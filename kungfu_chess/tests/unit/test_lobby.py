import pytest

from constants import PieceColor
from server.lobby import Lobby, LobbyError
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
from shared.messages.errors import ProtocolError
from shared.messages.parsers import parse_client_message, parse_server_message
from shared.messages.server_messages import (
    DisconnectCountdown,
    ErrorMessage,
    JoinAccepted,
    MatchFound,
    NoMatch,
    PlayerInfo,
    QueueStatus,
    RatingUpdate,
    RoomCreated,
    RoomJoined,
)
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


def test_lobby_seats_matched_players():
    lobby = Lobby()
    lobby.seat_match('Alice', 1200, 'c1', 'Bob', 1300, 'c2')

    white = lobby.get_by_color(PieceColor.WHITE.value)
    black = lobby.get_by_color(PieceColor.BLACK.value)
    assert white.username == 'Alice'
    assert white.rating == 1200
    assert black.username == 'Bob'
    assert black.rating == 1300
    assert lobby.is_ready() is True


def test_lobby_rejects_second_match_while_ready():
    lobby = Lobby()
    lobby.seat_match('Alice', 1200, 'c1', 'Bob', 1200, 'c2')

    with pytest.raises(LobbyError) as error:
        lobby.seat_match('Carol', 1200, 'c3', 'Dave', 1200, 'c4')
    assert error.value.code == 'room_full'


def test_lobby_leave_frees_seat():
    lobby = Lobby()
    lobby.seat_match('Alice', 1200, 'c1', 'Bob', 1200, 'c2')
    lobby.leave('c1')
    assert lobby.get_by_color(PieceColor.WHITE.value) is None
    assert lobby.get_by_color(PieceColor.BLACK.value).username == 'Bob'


def test_join_play_and_move_message_roundtrip():
    join = JoinRequest('Alice', 'pass1234')
    play = PlayRequest()
    create_room = CreateRoomRequest()
    join_room = JoinRoomRequest('ABC123')
    move = MoveRequest('WPe2e4')

    parsed_join = parse_client_message(encode_message(join.to_dict()))
    assert parsed_join.username == 'Alice'
    assert parsed_join.password == 'pass1234'
    assert parse_client_message(encode_message(play.to_dict())).TYPE == 'play'
    assert parse_client_message(
        encode_message(create_room.to_dict())
    ).TYPE == 'create_room'
    parsed_join_room = parse_client_message(
        encode_message(join_room.to_dict())
    )
    assert parsed_join_room.room_id == 'ABC123'
    assert parse_client_message(encode_message(move.to_dict())).command == 'WPe2e4'


def test_parse_client_message_rejects_unknown_type():
    with pytest.raises(ProtocolError):
        parse_client_message('{"type":"jump"}')


def test_server_message_roundtrips():
    accepted = JoinAccepted('Alice', 1200)
    parsed_accepted = parse_server_message(encode_message(accepted.to_dict()))
    assert parsed_accepted.username == 'Alice'
    assert parsed_accepted.rating == 1200

    queue = QueueStatus(60, 100)
    parsed_queue = parse_server_message(encode_message(queue.to_dict()))
    assert parsed_queue.timeout_seconds == 60

    match = MatchFound(
        'Alice',
        PieceColor.WHITE.value,
        1200,
        [
            PlayerInfo('Alice', PieceColor.WHITE.value, 1200),
            PlayerInfo('Bob', PieceColor.BLACK.value, 1210),
        ],
    )
    parsed_match = parse_server_message(encode_message(match.to_dict()))
    assert parsed_match.color == PieceColor.WHITE.value
    assert len(parsed_match.players) == 2

    no_match = NoMatch('no player found')
    assert parse_server_message(encode_message(no_match.to_dict())).TYPE == 'no_match'

    countdown = DisconnectCountdown('Alice', 15, 20)
    parsed_countdown = parse_server_message(
        encode_message(countdown.to_dict())
    )
    assert parsed_countdown.seconds_remaining == 15

    error = ErrorMessage('room_full', 'lobby supports only 2 players')
    assert parse_server_message(encode_message(error.to_dict())).code == 'room_full'

    rating_update = RatingUpdate(
        winner='Alice',
        loser='Bob',
        ratings={'Alice': 1216, 'Bob': 1184},
        reason='auto_resign',
    )
    parsed_ratings = parse_server_message(
        encode_message(rating_update.to_dict())
    )
    assert parsed_ratings.reason == 'auto_resign'
    assert parsed_ratings.ratings['Bob'] == 1184

    room_created = RoomCreated(
        'ABC123',
        'Alice',
        PieceColor.WHITE.value,
        1200,
        [PlayerInfo('Alice', PieceColor.WHITE.value, 1200)],
    )
    parsed_created = parse_server_message(
        encode_message(room_created.to_dict())
    )
    assert parsed_created.room_id == 'ABC123'
    assert parsed_created.role == PieceColor.WHITE.value

    room_joined = RoomJoined(
        'ABC123',
        'Bob',
        PieceColor.BLACK.value,
        1210,
        [
            PlayerInfo('Alice', PieceColor.WHITE.value, 1200),
            PlayerInfo('Bob', PieceColor.BLACK.value, 1210),
        ],
        game_started=True,
    )
    parsed_joined = parse_server_message(
        encode_message(room_joined.to_dict())
    )
    assert parsed_joined.game_started is True
    assert parsed_joined.role == PieceColor.BLACK.value
