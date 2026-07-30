from rules.pieces.bishop_rule import BishopRule
from rules.pieces.king_rule import KingRule
from rules.pieces.knight_rule import KnightRule
from rules.pieces.pawn_rule import PawnRule
from rules.pieces.queen_rule import QueenRule
from rules.pieces.rook_rule import RookRule

PIECE_RULES = {
    'R': RookRule(),
    'B': BishopRule(),
    'Q': QueenRule(),
    'N': KnightRule(),
    'K': KingRule(),
    'P': PawnRule(),
}
