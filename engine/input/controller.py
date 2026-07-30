import constants
from engine.game_engine import GameEngine
from input.board_mapper import BoardMapper
from model.position import Position


class Controller:
    def __init__(self, engine: GameEngine, cell_size: int = None):
        self.engine = engine
        self.selected_cell = None
        self.cell_size = constants.CELL_SIZE if cell_size is None else cell_size

    def _mapper(self) -> BoardMapper:
        board = self.engine.game_state.board
        return BoardMapper(board.width, board.height, self.cell_size)

    def click(self, x: int, y: int):
        if self.engine.game_state.game_over:
            return

        self.engine.arbiter.complete_pending(self.engine.game_state)
        if self.engine.game_state.game_over:
            return

        mapper = self._mapper()
        cell = mapper.pixel_to_cell(x, y)

        if self.selected_cell is not None and not mapper.is_inside_board(cell):
            self.selected_cell = None
            return

        if not mapper.is_inside_board(cell):
            return

        board = self.engine.game_state.board
        clicked_piece = board.piece_at(cell)

        if self.selected_cell is not None:
            source = self.selected_cell
            source_piece = board.piece_at(source)
            if source_piece is None:
                self.selected_cell = None
                return

            if source == cell:
                result = self.engine.request_jump(source)
            else:
                result = self.engine.request_move(source, cell)
            if result.is_accepted:
                self.selected_cell = None
            elif clicked_piece is not None and clicked_piece.color == source_piece.color:
                self.selected_cell = cell
            else:
                self.selected_cell = None
        elif clicked_piece is not None:
            if self.engine.arbiter.has_active_motion_from(cell.row, cell.col):
                return
            if (cell.row, cell.col) in self.engine.arbiter.active_jumps:
                return
            if self.engine.arbiter.is_piece_resting(clicked_piece.id):
                return
            self.selected_cell = cell

    def jump(self, x: int, y: int):
        mapper = self._mapper()
        cell = mapper.pixel_to_cell(x, y)
        self.engine.request_jump(cell)
