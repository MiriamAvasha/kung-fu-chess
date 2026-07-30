class Position:
    __slots__ = ('row', 'col')

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col

    def __eq__(self, other) -> bool:
        if not isinstance(other, Position):
            return False
        return self.row == other.row and self.col == other.col

    def __hash__(self) -> int:
        return hash((self.row, self.col))

    def __repr__(self) -> str:
        return f"Position({self.row}, {self.col})"
