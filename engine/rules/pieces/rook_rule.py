from model.board import Board
from model.piece import Piece
from rules.helpers import collect_sliding_destinations

# צריח רק ישר לכל הכיוונים
class RookRule:
    def legal_destinations(self, board: Board, piece: Piece) -> set:
        destinations = set()
        for row_step, col_step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            destinations |= collect_sliding_destinations(board, piece, row_step, col_step)
        return destinations
