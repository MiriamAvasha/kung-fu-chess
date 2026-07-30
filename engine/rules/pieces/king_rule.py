from model.board import Board
from model.piece import Piece
from model.position import Position


class KingRule:
    def legal_destinations(self, board: Board, piece: Piece) -> set:
        destinations = set()
        for d_row in (-1, 0, 1):
            for d_col in (-1, 0, 1):
                if d_row == 0 and d_col == 0:
                    continue
                dest = Position(piece.cell.row + d_row, piece.cell.col + d_col)
                if not board.is_inside(dest):
                    continue
                occupant = board.piece_at(dest)
                if occupant is None or occupant.color != piece.color:
                    destinations.add(dest)
        return destinations
