from model.board import Board
from model.piece import Piece
from rules.helpers import collect_sliding_destinations

# //רץ אלכסוני
class BishopRule:
    def legal_destinations(self, board: Board, piece: Piece) -> set:
        destinations = set()
        for row_step, col_step in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            destinations |= collect_sliding_destinations(board, piece, row_step, col_step)
        return destinations
