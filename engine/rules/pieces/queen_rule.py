from model.board import Board
from model.piece import Piece
from rules.pieces.bishop_rule import BishopRule
from rules.pieces.rook_rule import RookRule


class QueenRule:
    def __init__(self):
        self._rook = RookRule()
        self._bishop = BishopRule()

    def legal_destinations(self, board: Board, piece: Piece) -> set:
        return self._rook.legal_destinations(board, piece) | self._bishop.legal_destinations(board, piece)
