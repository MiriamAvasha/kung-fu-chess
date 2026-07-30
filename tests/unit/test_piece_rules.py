from model.position import Position
from rules.pieces.bishop_rule import BishopRule
from rules.pieces.king_rule import KingRule
from rules.pieces.knight_rule import KnightRule
from rules.pieces.pawn_rule import PawnRule
from rules.pieces.queen_rule import QueenRule
from rules.pieces.rook_rule import RookRule
from tests.conftest import make_board


def _dest_set(rule, board, piece):
    return {(p.row, p.col) for p in rule.legal_destinations(board, piece)}


class TestPawnRule:
    def test_white_single_and_double_from_start(self):
        board = make_board([['.'] * 8 for _ in range(8)])
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', '.', 'wP', '.', '.', '.', '.', '.'],
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(6, 2))
        assert _dest_set(PawnRule(), board, piece) == {(5, 2), (4, 2)}

    def test_black_single_and_double_from_start(self):
        board = make_board([
            ['.'] * 8,
            ['.', 'bP', '.', '.', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(1, 1))
        assert _dest_set(PawnRule(), board, piece) == {(2, 1), (3, 1)}

    def test_blocked_forward_no_moves(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', '.', 'bP', '.', '.', '.', '.', '.'],
            ['.', '.', 'wP', '.', '.', '.', '.', '.'],
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(6, 2))
        assert _dest_set(PawnRule(), board, piece) == set()

    def test_diagonal_capture_enemy_only(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', 'bN', '.', 'wR', '.', '.', '.', '.'],
            ['.', '.', 'wP', '.', '.', '.', '.', '.'],
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(6, 2))
        assert _dest_set(PawnRule(), board, piece) == {(5, 2), (4, 2), (5, 1)}

    def test_no_en_passant(self):
        # Enemy beside pawn is not capturable sideways — only forward-diagonal.
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', 'bP', 'wP', '.', '.', '.', '.', '.'],
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(6, 2))
        dests = _dest_set(PawnRule(), board, piece)
        assert (6, 1) not in dests


class TestRookRule:
    def test_slides_until_block_and_can_capture(self):
        board = make_board([
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', 'wR', '.', 'bP', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', 'wP', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
        ])
        piece = board.piece_at(Position(2, 2))
        dests = _dest_set(RookRule(), board, piece)
        assert (2, 3) in dests
        assert (2, 4) in dests  # capture enemy
        assert (2, 5) not in dests
        assert (3, 2) in dests
        assert (4, 2) not in dests  # blocked by ally


class TestBishopRule:
    def test_diagonal_slide_and_capture(self):
        board = make_board([
            ['.'] * 8,
            ['.', 'bP', '.', '.', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.', '.', '.', 'wB', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(3, 3))
        dests = _dest_set(BishopRule(), board, piece)
        assert (2, 2) in dests
        assert (1, 1) in dests  # capture
        assert (0, 0) not in dests


class TestQueenRule:
    def test_combines_rook_and_bishop_rays(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', '.', '.', 'wQ', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(3, 3))
        dests = _dest_set(QueenRule(), board, piece)
        assert (3, 0) in dests
        assert (0, 3) in dests
        assert (0, 0) in dests
        assert (5, 5) in dests


class TestKnightRule:
    def test_l_jumps_ignore_blockers(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.', '.', 'wP', 'wP', 'wP', '.', '.', '.'],
            ['.', '.', 'wP', 'wN', 'wP', '.', '.', '.'],
            ['.', '.', 'wP', 'wP', 'wP', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(3, 3))
        dests = _dest_set(KnightRule(), board, piece)
        assert (1, 2) in dests
        assert (1, 4) in dests
        assert (5, 2) in dests
        assert (4, 5) in dests
        assert (3, 4) not in dests  # not an L

    def test_cannot_land_on_ally(self):
        board = make_board([
            ['.'] * 8,
            ['.', '.', 'wP', '.', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.', '.', '.', 'wN', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(3, 3))
        assert (1, 2) not in _dest_set(KnightRule(), board, piece)


class TestKingRule:
    def test_one_square_any_direction(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.', '.', '.', 'wK', '.', '.', '.', '.'],
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
        ])
        piece = board.piece_at(Position(3, 3))
        dests = _dest_set(KingRule(), board, piece)
        assert dests == {
            (2, 2), (2, 3), (2, 4),
            (3, 2), (3, 4),
            (4, 2), (4, 3), (4, 4),
        }

    def test_no_castling(self):
        board = make_board([
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['wR', '.', '.', '.', 'wK', '.', '.', 'wR'],
        ])
        piece = board.piece_at(Position(7, 4))
        dests = _dest_set(KingRule(), board, piece)
        assert (7, 2) not in dests
        assert (7, 6) not in dests
