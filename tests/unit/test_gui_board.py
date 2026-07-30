import pygame

from client.gui.board_view import (
    NetworkBoardView,
    board_to_display,
    build_move_command,
    display_to_board,
    position_to_square,
)


def board_state():
    board = [['.'] * 8 for _ in range(8)]
    board[6][4] = 'wP'
    board[1][4] = 'bP'
    return {
        'board_width': 8,
        'board_height': 8,
        'board': board,
        'game_over': False,
        'server_time_ms': 0,
        'active_motions': [],
        'active_jumps': [],
    }


def board_view(role):
    view = NetworkBoardView.__new__(NetworkBoardView)
    view.state = board_state()
    view.role = role
    view.selected = None
    return view


def test_move_command_uses_server_protocol_format():
    assert position_to_square(6, 4) == 'e2'
    assert build_move_command('wP', (6, 4), (4, 4)) == 'wPe2e4'
    assert build_move_command('bP', (1, 4), (3, 4)) == 'bPe7e5'


def test_flipped_board_coordinates_round_trip():
    display_cell = board_to_display(1, 4, 8, 8, flipped=True)
    assert display_cell == (6, 3)
    assert display_to_board(*display_cell, 8, 8, flipped=True) == (1, 4)


def test_white_clicks_create_move_without_terminal_input():
    view = board_view('w')
    rect = pygame.Rect(0, 0, 800, 800)

    command, _ = view.handle_click((450, 650), rect)
    assert command is None
    assert view.selected == (6, 4)

    command, _ = view.handle_click((450, 450), rect)
    assert command == 'wPe2e4'
    assert view.selected is None


def test_clicking_the_same_piece_twice_creates_jump_command():
    view = board_view('w')
    rect = pygame.Rect(0, 0, 800, 800)

    view.handle_click((450, 650), rect)
    command, message = view.handle_click((450, 650), rect)

    assert command == 'wPe2e2'
    assert 'jump' in message.lower()
    assert view.selected is None


def test_black_board_is_rotated_for_clicks():
    view = board_view('b')
    rect = pygame.Rect(0, 0, 800, 800)

    view.handle_click((350, 650), rect)
    command, _ = view.handle_click((350, 450), rect)

    assert command == 'bPe7e5'


def test_spectators_cannot_create_moves():
    view = board_view('viewer')
    command, message = view.handle_click((450, 650), pygame.Rect(0, 0, 800, 800))

    assert command is None
    assert 'watching' in message.lower()
