from constants import PieceColor
from model.board import Board, board_from_token_rows
from model.piece import Piece, PieceState
from model.position import Position
from tests.conftest import make_board


class TestBoard:
    def test_from_token_rows_sets_size_and_pieces(self):
        board = make_board([
            ['bK', '.', 'wP'],
            ['.', '.', '.'],
        ])
        assert board.width == 3
        assert board.height == 2
        assert board.piece_at(Position(0, 0)).token == 'bK'
        assert board.piece_at(Position(0, 2)).token == 'wP'
        assert board.piece_at(Position(1, 1)) is None

    def test_is_inside(self):
        board = make_board([['.', '.'], ['.', '.']])
        assert board.is_inside(Position(0, 0))
        assert board.is_inside(Position(1, 1))
        assert not board.is_inside(Position(-1, 0))
        assert not board.is_inside(Position(0, 2))

    def test_pawn_start_rows_on_8x8(self):
        board = make_board([['.'] * 8 for _ in range(8)])
        assert board.get_pawn_start_row(PieceColor.WHITE.value) == 6
        assert board.get_pawn_start_row(PieceColor.BLACK.value) == 1

    def test_move_piece_updates_cell(self):
        board = make_board([['wR', '.', '.']])
        board.move_piece(Position(0, 0), Position(0, 2))
        assert board.piece_at(Position(0, 0)) is None
        assert board.piece_at(Position(0, 2)).token == 'wR'

    def test_remove_piece_marks_captured(self):
        board = make_board([['bN']])
        piece = board.piece_at(Position(0, 0))
        board.remove_piece(Position(0, 0))
        assert board.piece_at(Position(0, 0)) is None
        assert piece.state == PieceState.CAPTURED

    def test_to_token_grid(self):
        board = make_board([['wK', '.'], ['.', 'bQ']])
        assert board.to_token_grid() == [['wK', '.'], ['.', 'bQ']]

    def test_duplicate_occupancy_raises(self):
        board = Board()
        board.width = 1
        board.height = 1
        board.add_piece(Piece('w', 'K', Position(0, 0)))
        try:
            board.add_piece(Piece('b', 'Q', Position(0, 0)))
            assert False, 'expected ValueError'
        except ValueError:
            pass

    def test_empty_rows_returns_empty_board(self):
        board = board_from_token_rows([])
        assert board.width == 0
        assert board.height == 0
