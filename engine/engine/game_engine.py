import constants
from engine.results import GameSnapshot, MoveResult
from model.game_state import GameState
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import RuleEngine


class GameEngine:
    def __init__(self, game_state: GameState, rule_engine: RuleEngine, arbiter: RealTimeArbiter):
        self.game_state = game_state
        self.rule_engine = rule_engine
        self.arbiter = arbiter

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_state.game_over:
            return MoveResult(False, 'game_over')

        self.arbiter.complete_pending(self.game_state)
        if self.game_state.game_over:
            return MoveResult(False, 'game_over')

        validation = self.rule_engine.validate_move(self.game_state.board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)

        piece = self.game_state.board.piece_at(source)
        if self.arbiter.is_piece_resting(piece.id):
            return MoveResult(False, 'long_rest')
        if self.arbiter.has_opposite_color_route_conflict(
            self.game_state, piece.color, source.row, source.col, destination.row, destination.col
        ):
            return MoveResult(False, 'route_conflict')

        d_row = abs(destination.row - source.row)
        d_col = abs(destination.col - source.col)
        duration = max(d_row, d_col) * constants.get_speed_for_piece(piece.kind)
        self.arbiter.start_motion(
            self.game_state, source.row, source.col, destination.row, destination.col,
            piece.token, duration
        )
        return MoveResult(True, 'ok')

    def request_jump(self, cell: Position) -> MoveResult:
        if self.game_state.game_over:
            return MoveResult(False, 'game_over')

        self.arbiter.complete_pending(self.game_state)
        if self.game_state.game_over:
            return MoveResult(False, 'game_over')

        if not self.game_state.board.is_inside(cell):
            return MoveResult(False, 'outside_board')

        piece = self.game_state.board.piece_at(cell)
        if piece is None:
            return MoveResult(False, 'empty_source')

        if self.arbiter.is_piece_resting(piece.id):
            return MoveResult(False, 'long_rest')

        if self.arbiter.has_active_motion_from(cell.row, cell.col):
            return MoveResult(False, 'motion_in_progress')

        if (cell.row, cell.col) in self.arbiter.active_jumps:
            return MoveResult(False, 'jump_in_progress')

        self.arbiter.start_jump(self.game_state, cell.row, cell.col, piece.token)
        return MoveResult(True, 'ok')

    def wait(self, ms: int):
        self.arbiter.advance_time(self.game_state, ms)

    def snapshot(self, selected_cell=None) -> GameSnapshot:
        return GameSnapshot(
            self.game_state.board.width,
            self.game_state.board.height,
            self.game_state.board.to_token_grid(),
            self.game_state.game_over,
            selected_cell,
        )
