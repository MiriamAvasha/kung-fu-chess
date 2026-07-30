import pytest

from texttests.errors import ScriptParseError
from texttests.script_parser import ScriptParser


class TestScriptParser:
    def test_parse_click(self):
        parser = ScriptParser()
        assert parser.parse('click 100 200') == ('click', 100, 200)

    def test_parse_wait(self):
        parser = ScriptParser()
        assert parser.parse('wait 500') == ('wait', 500)

    def test_parse_jump(self):
        parser = ScriptParser()
        assert parser.parse('jump 50 50') == ('jump', 50, 50)

    def test_parse_print_board(self):
        parser = ScriptParser()
        assert parser.parse('print board') == ('print_board',)

    def test_empty_line_returns_none(self):
        parser = ScriptParser()
        assert parser.parse('') is None
        assert parser.parse('   ') is None

    def test_unknown_command_raises(self):
        parser = ScriptParser()
        with pytest.raises(ScriptParseError) as exc_info:
            parser.parse('move 1 2')
        assert exc_info.value.line == 'move 1 2'
        assert 'unknown command' in str(exc_info.value)

    def test_click_wrong_arity_raises(self):
        parser = ScriptParser()
        with pytest.raises(ScriptParseError) as exc_info:
            parser.parse('click 100')
        assert 'click requires exactly 2 coordinates' in str(exc_info.value)

    def test_click_non_integer_raises(self):
        parser = ScriptParser()
        with pytest.raises(ScriptParseError) as exc_info:
            parser.parse('click abc 200')
        assert 'x must be an integer' in str(exc_info.value)

    def test_print_invalid_raises(self):
        parser = ScriptParser()
        with pytest.raises(ScriptParseError) as exc_info:
            parser.parse('print score')
        assert 'print supports only' in str(exc_info.value)
