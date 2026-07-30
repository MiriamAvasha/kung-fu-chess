class Motion:
    def __init__(self, piece_id, piece_token, from_row, from_col, to_row, to_col, start_time, duration, order):
        self.piece_id = piece_id
        self.piece_token = piece_token
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.start_time = start_time
        self.duration = duration
        self.order = order
        # Original command — truncation only shortens the effective destination.
        self.original_to_row = to_row
        self.original_to_col = to_col
        self.original_duration = duration

    @property
    def arrival_time(self) -> int:
        return self.start_time + self.duration
