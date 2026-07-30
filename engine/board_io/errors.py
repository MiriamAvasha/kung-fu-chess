class BoardParseError(Exception):
    """Base class for board input parsing failures."""


class RowWidthMismatchError(BoardParseError):
    def __init__(self, expected_width: int, actual_width: int, row_index: int):
        self.expected_width = expected_width
        self.actual_width = actual_width
        self.row_index = row_index
        super().__init__(
            f"Row {row_index} has {actual_width} cells, expected {expected_width}"
        )


class UnknownTokenError(BoardParseError):
    def __init__(self, token: str, row_index: int):
        self.token = token
        self.row_index = row_index
        super().__init__(f"Unknown board token '{token}' in row {row_index}")
