from model.position import Position
from tests.conftest import make_controller, pixel_for


class TestController:
    def test_first_click_selects_piece(self):
        controller, engine = make_controller([['wR', '.', '.']])
        x, y = pixel_for(0, 0)
        controller.click(x, y)
        assert controller.selected_cell == Position(0, 0)

    def test_second_click_requests_move(self):
        controller, engine = make_controller([['wR', '.', '.']])
        x0, y0 = pixel_for(0, 0)
        x1, y1 = pixel_for(0, 2)
        controller.click(x0, y0)
        controller.click(x1, y1)
        assert controller.selected_cell is None
        assert engine.arbiter.has_active_motion_from(0, 0)
        engine.wait(2000)
        assert engine.game_state.board.piece_at(Position(0, 2)).token == 'wR'

    def test_click_empty_does_not_select(self):
        controller, _ = make_controller([['.', 'wR']])
        x, y = pixel_for(0, 0)
        controller.click(x, y)
        assert controller.selected_cell is None

    def test_outside_board_clears_selection(self):
        controller, _ = make_controller([['wR', '.']])
        x, y = pixel_for(0, 0)
        controller.click(x, y)
        assert controller.selected_cell == Position(0, 0)
        controller.click(5000, 5000)
        assert controller.selected_cell is None

    def test_ignores_input_when_game_over(self):
        controller, engine = make_controller([['wR', 'bK']])
        engine.game_state.game_over = True
        x, y = pixel_for(0, 0)
        controller.click(x, y)
        assert controller.selected_cell is None

    def test_jump_delegates_to_engine(self):
        controller, engine = make_controller([['wK']])
        x, y = pixel_for(0, 0)
        controller.jump(x, y)
        assert (0, 0) in engine.arbiter.active_jumps

    def test_second_click_on_selected_piece_starts_jump(self):
        controller, engine = make_controller([['wK']])
        x, y = pixel_for(0, 0)

        controller.click(x, y)
        controller.click(x, y)

        assert controller.selected_cell is None
        assert (0, 0) in engine.arbiter.active_jumps

    def test_cannot_select_piece_while_it_is_jumping(self):
        controller, engine = make_controller([['wK']])
        x, y = pixel_for(0, 0)
        assert engine.request_jump(Position(0, 0)).is_accepted

        controller.click(x, y)

        assert controller.selected_cell is None

    def test_cannot_select_piece_during_capture_rest(self):
        controller, engine = make_controller([['wR', 'bN']])
        engine.arbiter.set_long_rest_duration_provider(lambda _token: 500)
        assert engine.request_move(
            Position(0, 0),
            Position(0, 1),
        ).is_accepted
        engine.wait(1000)
        x, y = pixel_for(0, 1)

        controller.click(x, y)

        assert controller.selected_cell is None

    def test_cannot_select_piece_already_moving(self):
        controller, engine = make_controller([['wR', '.', '.']])
        x0, y0 = pixel_for(0, 0)
        x1, y1 = pixel_for(0, 2)
        controller.click(x0, y0)
        controller.click(x1, y1)
        controller.click(x0, y0)
        assert controller.selected_cell is None
