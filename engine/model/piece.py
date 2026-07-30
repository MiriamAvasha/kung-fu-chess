from model.position import Position


class PieceState:
    IDLE = 'idle'
    MOVING = 'moving'
    CAPTURED = 'captured'


class Piece:
    _next_id = 1

    def __init__(self, color: str, kind: str, cell: Position, state: str = PieceState.IDLE):
        self.id = Piece._next_id
        Piece._next_id += 1
        self.color = color
        self.kind = kind
        self.cell = cell
        self.state = state

    @property
    def token(self) -> str:
        return self.color + self.kind

    def __repr__(self) -> str:
        return f"Piece({self.token}@{self.cell})"
