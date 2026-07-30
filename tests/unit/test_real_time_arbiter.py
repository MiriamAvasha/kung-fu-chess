"""RealTimeArbiter layer tests — timing, captures, path blocks, jumps, promotion on land.

path_utils helpers belong to this layer's support code (rules/path_utils), so they
are covered here without inventing a separate product path.
"""
from model.piece import Piece
from model.position import Position
from rules.path_utils import (
    earlier_stop_along_path,
    is_earlier_arrival,
    last_square_before,
    path_cells,
    shared_path_cells,
    time_to_leave_cell,
    time_to_reach_cell,
)
from rules.promotion import (
    DEFAULT_PROMOTION_SERVICE,
    PawnToQueenPromotion,
    PromotionService,
)
from tests.conftest import make_board, make_engine


class TestPathUtils:
    def test_rook_path_includes_intermediates(self):
        path = path_cells(Position(0, 0), Position(0, 3))
        assert path == [Position(0, 0), Position(0, 1), Position(0, 2), Position(0, 3)]

    def test_bishop_path(self):
        path = path_cells(Position(2, 2), Position(0, 0))
        assert path == [Position(2, 2), Position(1, 1), Position(0, 0)]

    def test_knight_leap_has_no_intermediates(self):
        path = path_cells(Position(0, 0), Position(2, 1))
        assert path == [Position(0, 0), Position(2, 1)]

    def test_last_square_before_collision(self):
        stop = last_square_before(Position(0, 0), Position(0, 4), Position(0, 3))
        assert stop == Position(0, 2)

    def test_time_to_reach_scales_along_path(self):
        t = time_to_reach_cell(0, 3000, Position(0, 0), Position(0, 3), Position(0, 1))
        assert t == 1000

    def test_time_to_leave_destination_is_none(self):
        leave = time_to_leave_cell(0, 2000, Position(0, 0), Position(0, 2), Position(0, 2))
        assert leave is None

    def test_shared_path_cells(self):
        shared = shared_path_cells(
            Position(0, 0), Position(0, 4),
            Position(2, 2), Position(0, 2),
        )
        assert Position(0, 2) in shared

    def test_earlier_arrival_uses_order_on_tie(self):
        assert is_earlier_arrival(100, 1, 100, 2)
        assert not is_earlier_arrival(100, 2, 100, 1)
        assert is_earlier_arrival(50, 9, 100, 1)

    def test_earlier_stop_along_path_picks_closer(self):
        better = earlier_stop_along_path(
            Position(0, 0), Position(0, 5),
            Position(0, 4), Position(0, 2),
        )
        assert better == Position(0, 2)


class TestPromotionRules:
    def test_white_pawn_promotes_on_row_0(self):
        board = make_board([['.'], ['wP']])
        piece = board.piece_at(Position(1, 0))
        assert PawnToQueenPromotion().promoted_kind(board, piece, Position(0, 0)) == 'Q'

    def test_black_pawn_promotes_on_last_row(self):
        board = make_board([['bP'], ['.']])
        piece = board.piece_at(Position(0, 0))
        assert PawnToQueenPromotion().promoted_kind(board, piece, Position(1, 0)) == 'Q'

    def test_non_pawn_does_not_promote(self):
        board = make_board([['.'], ['wR']])
        piece = board.piece_at(Position(1, 0))
        assert PawnToQueenPromotion().promoted_kind(board, piece, Position(0, 0)) is None

    def test_pawn_not_on_last_rank(self):
        board = make_board([['.'], ['.'], ['wP']])
        piece = board.piece_at(Position(2, 0))
        assert PawnToQueenPromotion().promoted_kind(board, piece, Position(1, 0)) is None

    def test_default_service_resolves_queen(self):
        board = make_board([['.'] * 8 for _ in range(8)])
        piece = Piece('w', 'P', Position(1, 0))
        assert DEFAULT_PROMOTION_SERVICE.resolve(board, piece, Position(0, 0)) == 'Q'

    def test_empty_service_returns_none(self):
        board = make_board([['.'], ['wP']])
        piece = board.piece_at(Position(1, 0))
        assert PromotionService([]).resolve(board, piece, Position(0, 0)) is None


class TestCaptures:
    def test_later_arriver_captures_idle_enemy(self):
        engine = make_engine([['wR', '.', 'bN']])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'wR'
        assert len(engine.game_state.board.all_pieces()) == 1

    def test_later_eats_earlier_on_same_destination(self):
        engine = make_engine([
            ['wR', '.', '.'],
            ['.', '.', '.'],
            ['.', '.', 'bR'],
        ])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(500)
        engine.request_move(Position(2, 2), Position(0, 2))
        engine.wait(2500)
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'bR'
        assert engine.game_state.board.piece_at(Position(0, 0)) is None
        assert engine.game_state.board.piece_at(Position(2, 2)) is None

    def test_head_on_swap_later_eats_earlier(self):
        engine = make_engine([['wR', '.', 'bR']])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.request_move(Position(0, 2), Position(0, 0))
        engine.wait(2000)
        assert engine.game_state.board.piece_at(Position(0, 0)).token == 'bR'
        assert engine.game_state.board.piece_at(Position(0, 2)) is None

    def test_same_color_never_captures_on_destination(self):
        engine = make_engine([
            ['wR', '.', '.'],
            ['.', '.', '.'],
            ['.', '.', 'wR'],
        ])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(500)
        engine.request_move(Position(2, 2), Position(0, 2))
        engine.wait(2500)
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'wR'
        assert engine.game_state.board.piece_at(Position(1, 2)).token == 'wR'


class TestSameColorPathBlocks:
    def test_later_ally_stops_before_shared_cell(self):
        engine = make_engine([['wR', '.', '.', '.', 'wR']])
        engine.request_move(Position(0, 0), Position(0, 3))
        engine.request_move(Position(0, 4), Position(0, 1))
        engine.wait(4000)
        pieces = {(p.cell.row, p.cell.col): p.token for p in engine.game_state.board.all_pieces()}
        assert list(pieces.values()).count('wR') == 2
        assert (0, 3) in pieces or (0, 2) in pieces or (0, 1) in pieces

    def test_static_ally_on_path_truncates(self):
        engine = make_engine([
            ['wR', '.', '.', '.', '.'],
            ['.', '.', 'wR', '.', '.'],
        ])
        assert engine.request_move(Position(0, 0), Position(0, 4)).is_accepted
        assert engine.request_move(Position(1, 2), Position(0, 2)).is_accepted
        engine.wait(5000)
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'wR'
        assert engine.game_state.board.piece_at(Position(0, 1)).token == 'wR'
        assert engine.game_state.board.piece_at(Position(0, 4)) is None


class TestAirborneJump:
    def test_airborne_defender_eats_attacker(self):
        engine = make_engine([['wR', 'bN']])
        assert engine.request_jump(Position(0, 1)).is_accepted
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        assert engine.game_state.board.piece_at(Position(0, 1)).token == 'bN'
        assert engine.game_state.board.piece_at(Position(0, 0)) is None

    def test_airborne_result_uses_arrival_time_when_frame_overshoots(self):
        engine = make_engine([['wR', 'bN']])
        assert engine.request_jump(Position(0, 1)).is_accepted
        assert engine.request_move(
            Position(0, 0),
            Position(0, 1),
        ).is_accepted

        engine.wait(1050)

        assert engine.game_state.board.piece_at(Position(0, 1)).token == 'bN'
        assert engine.game_state.board.piece_at(Position(0, 0)) is None
        assert (0, 1) not in engine.arbiter.active_jumps

    def test_airborne_defender_rests_after_eating_attacker(self):
        engine = make_engine([['wR', 'bN']])
        defender = engine.game_state.board.piece_at(Position(0, 1))
        engine.arbiter.set_long_rest_duration_provider(lambda _token: 500)
        assert engine.request_jump(Position(0, 1)).is_accepted
        assert engine.request_move(
            Position(0, 0),
            Position(0, 1),
        ).is_accepted

        engine.wait(1000)

        assert engine.arbiter.is_piece_resting(defender.id)

    def test_king_attacker_eaten_by_airborne_ends_game(self):
        engine = make_engine([['wK', 'bN']])
        engine.request_jump(Position(0, 1))
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        assert engine.game_state.game_over is True
        assert engine.game_state.board.piece_at(Position(0, 0)) is None
        assert engine.game_state.board.piece_at(Position(0, 1)).token == 'bN'


class TestGameOverAndPromotionOnLand:
    def test_capturing_king_ends_game(self):
        engine = make_engine([['wR', '.', 'bK']])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        assert engine.game_state.game_over is True
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'wR'

    def test_white_pawn_promotes_to_queen(self):
        engine = make_engine([
            ['.', '.', '.'],
            ['wP', '.', '.'],
            ['.', '.', '.'],
        ])
        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)
        assert engine.game_state.board.piece_at(Position(0, 0)).token == 'wQ'

    def test_black_pawn_promotes_to_queen(self):
        engine = make_engine([['.'], ['bP'], ['.']])
        engine.request_move(Position(1, 0), Position(2, 0))
        engine.wait(1000)
        assert engine.game_state.board.piece_at(Position(2, 0)).token == 'bQ'
