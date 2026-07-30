class MoveValidation:
    def __init__(self, is_valid: bool, reason: str = 'ok'):
        self.is_valid = is_valid
        self.reason = reason


class MoveResult:
    def __init__(self, is_accepted: bool, reason: str = 'ok'):
        self.is_accepted = is_accepted
        self.reason = reason


class GameSnapshot:
    def __init__(self, board_width, board_height, token_grid, game_over, selected_cell=None):
        self.board_width = board_width
        self.board_height = board_height
        self.token_grid = token_grid
        self.game_over = game_over
        self.selected_cell = selected_cell
