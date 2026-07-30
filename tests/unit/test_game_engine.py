import constants
from model.position import Position
from tests.conftest import make_engine


class TestGameEngineMoves:
    def test_legal_move_starts_and_completes(self):
        engine = make_engine([
            ['wR', '.', '.', '.'],
            ['.', '.', '.', '.'],
        ])
        result = engine.request_move(Position(0, 0), Position(0, 3))
        assert result.is_accepted
        assert result.reason == 'ok'
        engine.wait(3000)
        assert engine.game_state.board.piece_at(Position(0, 3)).token == 'wR'
        assert engine.game_state.board.piece_at(Position(0, 0)) is None

    def test_rejects_illegal_move(self):
        engine = make_engine([['wK', '.', '.']])
        result = engine.request_move(Position(0, 0), Position(0, 2))
        assert not result.is_accepted
        assert result.reason == 'illegal_piece_move'

    def test_rejects_when_game_over(self):
        engine = make_engine([['wK', 'bR']])
        engine.game_state.game_over = True
        result = engine.request_move(Position(0, 1), Position(0, 0))
        assert not result.is_accepted
        assert result.reason == 'game_over'

    def test_duration_is_chebyshev_times_speed(self):
        engine = make_engine([
            ['wR', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
        ])
        engine.request_move(Position(0, 0), Position(0, 3))
        motion = next(iter(engine.arbiter.active_motions.values()))
        assert motion.duration == 3 * constants.get_speed_for_piece('R')

    def test_capturer_cannot_move_or_jump_until_long_rest_ends(self):
        engine = make_engine([['wR', 'bN', '.']])
        engine.arbiter.set_long_rest_duration_provider(lambda _token, _state='long_rest': 500)
        assert engine.request_move(
            Position(0, 0),
            Position(0, 1),
        ).is_accepted
        engine.wait(1000)

        move_result = engine.request_move(
            Position(0, 1),
            Position(0, 2),
        )
        jump_result = engine.request_jump(Position(0, 1))

        assert not move_result.is_accepted
        assert move_result.reason == 'long_rest'
        assert not jump_result.is_accepted
        assert jump_result.reason == 'long_rest'

        engine.wait(500)
        assert engine.request_move(
            Position(0, 1),
            Position(0, 2),
        ).is_accepted

    def test_move_without_capture_also_starts_long_rest(self):
        engine = make_engine([['wR', '.', '.']])
        engine.arbiter.set_long_rest_duration_provider(lambda _token, _state='long_rest': 500)
        assert engine.request_move(
            Position(0, 0),
            Position(0, 1),
        ).is_accepted

        engine.wait(1000)

        assert engine.arbiter.active_long_rests
        assert not engine.request_move(
            Position(0, 1),
            Position(0, 2),
        ).is_accepted

        engine.wait(500)
        assert engine.request_move(
            Position(0, 1),
            Position(0, 2),
        ).is_accepted

    def test_jump_starts_short_rest_when_finished(self):
        engine = make_engine([['wK']])
        engine.arbiter.set_long_rest_duration_provider(
            lambda _token, state='long_rest': 300 if state == 'short_rest' else 500
        )
        assert engine.request_jump(Position(0, 0)).is_accepted
        engine.wait(constants.JUMP_DURATION + 1)

        assert (0, 0) not in engine.arbiter.active_jumps
        assert engine.arbiter.active_long_rests
        blocked = engine.request_jump(Position(0, 0))
        assert not blocked.is_accepted
        assert blocked.reason == 'long_rest'


class TestGameEngineJump:
    def test_jump_accepted_and_expires(self):
        engine = make_engine([['wK']])
        result = engine.request_jump(Position(0, 0))
        assert result.is_accepted
        assert (0, 0) in engine.arbiter.active_jumps
        engine.wait(constants.JUMP_DURATION + 1)
        assert (0, 0) not in engine.arbiter.active_jumps
        # Without a rest-duration provider, jump expiry does not block a new jump.
        assert engine.request_jump(Position(0, 0)).is_accepted

    def test_jump_empty_source(self):
        engine = make_engine([['.']])
        result = engine.request_jump(Position(0, 0))
        assert not result.is_accepted
        assert result.reason == 'empty_source'

    def test_jump_while_moving_rejected(self):
        engine = make_engine([['wR', '.', '.']])
        engine.request_move(Position(0, 0), Position(0, 2))
        result = engine.request_jump(Position(0, 0))
        assert not result.is_accepted
        assert result.reason == 'motion_in_progress'

    def test_jump_while_already_jumping_rejected(self):
        engine = make_engine([['wK']])
        assert engine.request_jump(Position(0, 0)).is_accepted
        result = engine.request_jump(Position(0, 0))
        assert not result.is_accepted
        assert result.reason == 'jump_in_progress'


class TestRouteConflict:
    def test_opposite_color_same_row_overlap_rejected(self):
        engine = make_engine([
            ['wR', '.', '.', '.', 'bR'],
        ])
        assert engine.request_move(Position(0, 0), Position(0, 3)).is_accepted
        result = engine.request_move(Position(0, 4), Position(0, 1))
        assert not result.is_accepted
        assert result.reason == 'route_conflict'

    def test_head_on_swap_not_route_conflict(self):
        engine = make_engine([
            ['wR', '.', 'bR'],
        ])
        assert engine.request_move(Position(0, 0), Position(0, 2)).is_accepted
        result = engine.request_move(Position(0, 2), Position(0, 0))
        assert result.is_accepted
