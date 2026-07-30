from typing import Dict, List, Optional, Tuple

import constants
from model.piece import Piece, PieceState
from model.position import Position

# כמה שורות מהקצה הרגלי יכול לבצע צעד כפול
PAWN_START_ROW_OFFSET = 1


class Board:
    def __init__(self):
        self.width = 0
        self.height = 0
        self._cells: Dict[Tuple[int, int], Piece] = {}

    def is_inside(self, position: Position) -> bool:
        return 0 <= position.row < self.height and 0 <= position.col < self.width

    def get_pawn_start_row(self, color: str) -> int:
        if color == constants.PieceColor.WHITE.value:
            return self.height - 1 - PAWN_START_ROW_OFFSET
        return PAWN_START_ROW_OFFSET

    def piece_at(self, position: Position):
        return self._cells.get((position.row, position.col))

    def add_piece(self, piece: Piece):
        key = (piece.cell.row, piece.cell.col)
        if key in self._cells:
            raise ValueError("duplicate occupancy")
        self._cells[key] = piece

    def remove_piece(self, position: Position):
        key = (position.row, position.col)
        piece = self._cells.pop(key, None)
        if piece is not None:
            piece.state = PieceState.CAPTURED

    def move_piece(self, source: Position, destination: Position, new_kind: Optional[str] = None):
        piece = self._cells.pop((source.row, source.col))
        piece.cell = destination
        piece.state = PieceState.IDLE
        if new_kind is not None:
            piece.kind = new_kind
        self._cells[(destination.row, destination.col)] = piece

    def all_pieces(self):
        return list(self._cells.values())

    def to_token_grid(self) -> List[List[str]]:
        grid = [[constants.EMPTY_CELL for _ in range(self.width)] for _ in range(self.height)]
        for piece in self._cells.values():
            grid[piece.cell.row][piece.cell.col] = piece.token
        return grid


def board_from_token_rows(rows: List[List[str]]) -> Board:
    Piece._next_id = 1
    board = Board()
    if not rows:
        return board
    board.height = len(rows)
    board.width = len(rows[0])
    for row_idx, row in enumerate(rows):
        for col_idx, token in enumerate(row):
            if token != constants.EMPTY_CELL:
                board.add_piece(Piece(token[0], token[1], Position(row_idx, col_idx)))
    return board
