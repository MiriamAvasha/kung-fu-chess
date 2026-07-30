from texttests.errors import ScriptParseError


class ScriptParser:
    def __init__(self):
        self._parsers = {
            'click': self._parse_click,
            'wait': self._parse_wait,
            'jump': self._parse_jump,
            'print': self._parse_print,
        }

    def parse(self, command_line: str):
        parts = command_line.split()
        if not parts:
            return None
        parser = self._parsers.get(parts[0])
        if parser is None:
            raise ScriptParseError(command_line, f"unknown command '{parts[0]}'")
        return parser(command_line, parts)

    def _parse_int(self, command_line: str, value: str, field_name: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ScriptParseError(
                command_line,
                f"{field_name} must be an integer, got '{value}'",
            ) from exc

    def _parse_click(self, command_line: str, parts):
        if len(parts) != 3:
            raise ScriptParseError(command_line, "click requires exactly 2 coordinates: click x y")
        return (
            'click',
            self._parse_int(command_line, parts[1], 'x'),
            self._parse_int(command_line, parts[2], 'y'),
        )

    def _parse_wait(self, command_line: str, parts):
        if len(parts) != 2:
            raise ScriptParseError(command_line, "wait requires exactly 1 value: wait ms")
        return ('wait', self._parse_int(command_line, parts[1], 'ms'))

    def _parse_jump(self, command_line: str, parts):
        if len(parts) != 3:
            raise ScriptParseError(command_line, "jump requires exactly 2 coordinates: jump x y")
        return (
            'jump',
            self._parse_int(command_line, parts[1], 'x'),
            self._parse_int(command_line, parts[2], 'y'),
        )

    def _parse_print(self, command_line: str, parts):
        if len(parts) != 2 or parts[1] != 'board':
            raise ScriptParseError(command_line, "print supports only: print board")
        return ('print_board',)
