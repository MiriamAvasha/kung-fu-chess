class LongRest:
    def __init__(
        self,
        piece_id: int,
        piece_token: str,
        row: int,
        col: int,
        start_time: int,
        duration: int,
    ):
        self.piece_id = piece_id
        self.piece_token = piece_token
        self.row = row
        self.col = col
        self.start_time = start_time
        self.duration = duration

    @property
    def end_time(self) -> int:
        return self.start_time + self.duration

    def remaining_ms(self, current_time: int) -> int:
        return max(0, self.end_time - current_time)

    def remaining_ratio(self, current_time: int) -> float:
        if self.duration <= 0:
            return 0.0
        return min(1.0, self.remaining_ms(current_time) / float(self.duration))
