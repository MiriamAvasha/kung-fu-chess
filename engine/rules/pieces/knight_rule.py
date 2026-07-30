from model.board import Board
from model.piece import Piece
from model.position import Position


class KnightRule:
    def legal_destinations(self, board: Board, piece: Piece) -> set:
        destinations = set()
        for d_row, d_col in ((2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)):
            dest = Position(piece.cell.row + d_row, piece.cell.col + d_col)
            if not board.is_inside(dest):
                continue
            occupant = board.piece_at(dest)
            if occupant is None or occupant.color != piece.color:
                destinations.add(dest)
        return destinations
