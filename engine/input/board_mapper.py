import constants
from model.position import Position


class BoardMapper:
    def __init__(self, board_width: int, board_height: int, cell_size: int = None):
        self.board_width = board_width
        self.board_height = board_height
        self.cell_size = constants.CELL_SIZE if cell_size is None else cell_size

    def pixel_to_cell(self, x: int, y: int) -> Position:
        return Position(y // self.cell_size, x // self.cell_size)

    def is_inside_board(self, position: Position) -> bool:
        return 0 <= position.row < self.board_height and 0 <= position.col < self.board_width
