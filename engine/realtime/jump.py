import constants


class Jump:
    def __init__(self, piece_id, piece_token, row, col, start_time):
        self.piece_id = piece_id
        self.piece_token = piece_token
        self.row = row
        self.col = col
        self.start_time = start_time
        self.duration = constants.JUMP_DURATION

    @property
    def end_time(self) -> int:
        return self.start_time + self.duration
