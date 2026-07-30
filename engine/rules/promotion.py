from typing import List, Optional

from constants import FIRST_ROW, VALID_PIECES, PieceColor, PieceKind
from model.board import Board
from model.piece import Piece
from model.position import Position


class PromotionRule:

    def promoted_kind(self, board: Board, piece: Piece, destination: Position) -> Optional[PieceKind]:
        raise NotImplementedError

class PawnToQueenPromotion(PromotionRule):
    source_kind = PieceKind.PAWN
    target_kind = PieceKind.QUEEN

    def promoted_kind(self, board: Board, piece: Piece, destination: Position) -> Optional[PieceKind]:
        try:
            current_kind = PieceKind(piece.kind)
            current_color = PieceColor(piece.color)
        except ValueError:
            return None

        if current_kind is not self.source_kind:
            return None

        last_row = board.height - 1
        if current_color is PieceColor.WHITE and destination.row == FIRST_ROW:
            return self.target_kind
        if current_color is PieceColor.BLACK and destination.row == last_row:
            return self.target_kind
        return None


class PromotionService:
    def __init__(self, rules: List[PromotionRule]):
        self.rules = list(rules)

    def resolve(self, board: Board, piece: Piece, destination: Position) -> Optional[str]:
        for rule in self.rules:
            kind = rule.promoted_kind(board, piece, destination)
            if kind is None:
                continue
            value = kind.value
            if value in VALID_PIECES:
                return value
        return None

ACTIVE_PROMOTION_RULES = [PawnToQueenPromotion()]
DEFAULT_PROMOTION_SERVICE = PromotionService(ACTIVE_PROMOTION_RULES)
