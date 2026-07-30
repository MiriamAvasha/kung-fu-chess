from engine.results import MoveValidation
from model.board import Board
from model.position import Position
from .piece_rules import PIECE_RULES


class RuleEngine:
    def validate_move(self, board: Board, source: Position, destination: Position) -> MoveValidation:
        if not board.is_inside(source) or not board.is_inside(destination):
            return MoveValidation(False, 'outside_board')

        if source == destination:
            return MoveValidation(False, 'illegal_piece_move')

        piece = board.piece_at(source)
        if piece is None:
            return MoveValidation(False, 'empty_source')

        occupant = board.piece_at(destination)
        if occupant is not None and occupant.color == piece.color:
            return MoveValidation(False, 'friendly_destination')

        rule = PIECE_RULES.get(piece.kind)
        if rule is None:
            return MoveValidation(False, 'illegal_piece_move')

        if destination not in rule.legal_destinations(board, piece):
            return MoveValidation(False, 'illegal_piece_move')

        return MoveValidation(True, 'ok')
