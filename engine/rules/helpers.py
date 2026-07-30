from model.board import Board
from model.piece import Piece
from model.position import Position


def collect_sliding_destinations(board: Board, piece: Piece, row_step: int, col_step: int) -> set:
    destinations = set()
    row = piece.cell.row + row_step
    col = piece.cell.col + col_step

    while board.is_inside(Position(row, col)):
        occupant = board.piece_at(Position(row, col))
        if occupant is None:
            destinations.add(Position(row, col))
        else:
            if occupant.color != piece.color:
                destinations.add(Position(row, col))
            break
        row += row_step
        col += col_step

    return destinations
