import json

import pytest

from constants import PieceColor
from engine.game_factory import build_engine
from model.position import Position
from server.game_session import GameSession
from server.move_parser import (
    MoveCommandError,
    parse_move_command,
    square_to_position,
)
from shared.protocol import encode_message


def test_square_to_position_uses_chess_coordinates():
    assert square_to_position('a8') == Position(0, 0)
    assert square_to_position('e2') == Position(6, 4)
    assert square_to_position('h1') == Position(7, 7)


def test_parse_move_command_normalizes_piece_token():
    command = parse_move_command('WPe2e4')

    assert command.token == 'wP'
    assert command.source == Position(6, 4)
    assert command.destination == Position(4, 4)


@pytest.mark.parametrize(
    'raw_command',
    ['', 'move e2 e4', 'WPe9e4', 'WXe2e4', 'WPe2'],
)
def test_parse_move_command_rejects_invalid_format(raw_command):
    with pytest.raises(MoveCommandError):
        parse_move_command(raw_command)


def test_session_accepts_move_and_advances_authoritative_board():
    session = GameSession(build_engine())

    result = session.handle_command('WPe2e4', PieceColor.WHITE.value)

    assert result['type'] == 'move_result'
    assert result['accepted'] is True
    assert result['state']['active_motions']

    assert session.advance(10000) is True
    state = session.game_state_message()['state']
    assert state['board'][6][4] == '.'
    assert state['board'][4][4] == 'wP'
    assert state['active_motions'] == []


def test_session_rejects_piece_prefix_that_does_not_match_source():
    session = GameSession(build_engine())

    result = session.handle_command('WNd1f2', PieceColor.WHITE.value)

    assert result['accepted'] is False
    assert result['reason'] == 'piece_mismatch'


def test_session_rejects_wrong_player_color():
    session = GameSession(build_engine())

    result = session.handle_command('WPe2e4', PieceColor.BLACK.value)

    assert result['accepted'] is False
    assert result['reason'] == 'wrong_color'


def test_session_rejects_illegal_move_without_changing_board():
    session = GameSession(build_engine())
    original_board = session.initial_message()['state']['board']

    result = session.handle_command('WPe2e5', PieceColor.WHITE.value)

    assert result['accepted'] is False
    assert result['reason'] == 'illegal_piece_move'
    assert result['state']['board'] == original_board


def test_session_returns_protocol_error_for_malformed_command():
    result = GameSession(build_engine()).handle_command(
        'not-a-move',
        PieceColor.WHITE.value,
    )

    assert result == {
        'type': 'error',
        'code': 'invalid_command',
        'message': 'expected move format such as WPe2e4',
    }


def test_protocol_encodes_json_message():
    encoded = encode_message(
        GameSession(build_engine()).initial_message()
    )

    decoded = json.loads(encoded)
    assert decoded['type'] == 'initial_state'
    assert decoded['state']['board_width'] == 8
    assert decoded['state']['board_height'] == 8
