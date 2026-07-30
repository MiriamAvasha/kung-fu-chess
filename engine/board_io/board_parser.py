import constants
from board_io.errors import RowWidthMismatchError, UnknownTokenError
from model.board import board_from_token_rows
from model.game_state import GameState


class BoardParser:
    def __init__(self):
        self._width = None
        self._rows = []

    def add_row(self, row_str: str) -> GameState:
        tokens = row_str.strip().split()
        if not tokens:
            return GameState(board_from_token_rows(self._rows))

        row_index = len(self._rows) + 1

        if self._width is None:
            self._width = len(tokens)
        elif len(tokens) != self._width:
            raise RowWidthMismatchError(self._width, len(tokens), row_index)

        for token in tokens:
            if not constants.is_valid_token(token):
                raise UnknownTokenError(token, row_index)

        self._rows.append(tokens)
        return GameState(board_from_token_rows(self._rows))
