from model.position import Position
from rules.rule_engine import RuleEngine
from tests.conftest import make_board


class TestRuleEngine:
    def setup_method(self):
        self.rules = RuleEngine()

    def test_outside_board(self):
        board = make_board([['wK', '.'], ['.', '.']])
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 5))
        assert not result.is_valid
        assert result.reason == 'outside_board'

    def test_empty_source(self):
        board = make_board([['.', '.'], ['.', '.']])
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 1))
        assert not result.is_valid
        assert result.reason == 'empty_source'

    def test_same_square_illegal(self):
        board = make_board([['wK']])
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 0))
        assert not result.is_valid
        assert result.reason == 'illegal_piece_move'

    def test_friendly_destination(self):
        board = make_board([['wK', 'wP']])
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 1))
        assert not result.is_valid
        assert result.reason == 'friendly_destination'

    def test_illegal_piece_pattern(self):
        board = make_board([
            ['wK', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
        ])
        # King cannot jump two squares
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 2))
        assert not result.is_valid
        assert result.reason == 'illegal_piece_move'

    def test_valid_move(self):
        board = make_board([
            ['wR', '.', '.', '.'],
            ['.', '.', '.', '.'],
        ])
        result = self.rules.validate_move(board, Position(0, 0), Position(0, 3))
        assert result.is_valid
        assert result.reason == 'ok'
