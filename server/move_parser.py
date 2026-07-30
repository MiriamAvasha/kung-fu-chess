import re

from model.position import Position


MOVE_PATTERN = re.compile(
    r'^(?P<color>[wb])(?P<kind>[kqrbnp])'
    r'(?P<source>[a-h][1-8])(?P<destination>[a-h][1-8])$',
    re.IGNORECASE,
)


class MoveCommandError(ValueError):
    pass


class MoveCommand:
    def __init__(
        self,
        token: str,
        source: Position,
        destination: Position,
        raw: str,
    ):
        self.token = token
        self.source = source
        self.destination = destination
        self.raw = raw


def square_to_position(square: str) -> Position:
    normalized = square.lower()
    column = ord(normalized[0]) - ord('a')
    row = 8 - int(normalized[1])
    return Position(row, column)


def parse_move_command(raw_command: str) -> MoveCommand:
    if not isinstance(raw_command, str):
        raise MoveCommandError('move command must be text')

    command = raw_command.strip()
    match = MOVE_PATTERN.fullmatch(command)
    if match is None:
        raise MoveCommandError(
            'expected move format such as WPe2e4'
        )

    color = match.group('color').lower()
    kind = match.group('kind').upper()
    source = square_to_position(match.group('source'))
    destination = square_to_position(match.group('destination'))
    return MoveCommand(color + kind, source, destination, command)
