from board_io.board_printer import BoardPrinter
from model.game_state import GameState
from tests.conftest import make_board


class TestBoardPrinter:
    def test_prints_space_separated_token_rows(self, capsys):
        state = GameState(make_board([
            ['wR', '.', 'bK'],
            ['.', 'wP', '.'],
        ]))
        BoardPrinter().print_board(state)
        out = capsys.readouterr().out
        assert out == 'wR . bK\n. wP .\n'

    def test_prints_empty_board(self, capsys):
        state = GameState(make_board([['.', '.'], ['.', '.']]))
        BoardPrinter().print_board(state)
        out = capsys.readouterr().out
        assert out == '. .\n. .\n'
