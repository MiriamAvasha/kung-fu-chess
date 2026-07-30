from input.board_mapper import BoardMapper
from model.position import Position


class TestBoardMapper:
    def test_pixel_to_cell_uses_cell_size(self):
        mapper = BoardMapper(8, 8, cell_size=100)
        assert mapper.pixel_to_cell(50, 150) == Position(1, 0)
        assert mapper.pixel_to_cell(250, 50) == Position(0, 2)

    def test_is_inside_board(self):
        mapper = BoardMapper(2, 2, cell_size=50)
        assert mapper.is_inside_board(Position(0, 0))
        assert mapper.is_inside_board(Position(1, 1))
        assert not mapper.is_inside_board(Position(2, 0))
