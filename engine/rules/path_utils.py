from model.position import Position


def path_cells(source: Position, destination: Position):
    """Squares from source to destination inclusive (knight-like jumps have no intermediates)."""
    cells = [Position(source.row, source.col)]
    d_row = destination.row - source.row
    d_col = destination.col - source.col
    steps = max(abs(d_row), abs(d_col))
    if steps == 0:
        return cells

    # Non-sliding leap (e.g. knight): only endpoints.
    if d_row != 0 and d_col != 0 and abs(d_row) != abs(d_col):
        cells.append(Position(destination.row, destination.col))
        return cells

    row_step = 0 if d_row == 0 else d_row // abs(d_row)
    col_step = 0 if d_col == 0 else d_col // abs(d_col)
    row, col = source.row, source.col
    for _ in range(steps):
        row += row_step
        col += col_step
        cells.append(Position(row, col))
    return cells


def last_square_before(source: Position, destination: Position, collision: Position) -> Position:
    """Closest square reached on the path before the collision square."""
    path = path_cells(source, destination)
    for index, cell in enumerate(path):
        if cell == collision:
            if index == 0:
                return path[0]
            return path[index - 1]
    if len(path) >= 2:
        return path[-2]
    return path[0]


def time_to_reach_cell(start_time: int, duration: int, source: Position, destination: Position, cell: Position):
    """Absolute time when the mover reaches `cell` along source→destination, or None."""
    path = path_cells(source, destination)
    steps = len(path) - 1
    for index, step_cell in enumerate(path):
        if step_cell != cell:
            continue
        if steps <= 0:
            return start_time
        return start_time + int(round(duration * index / float(steps)))
    return None


def time_to_leave_cell(start_time: int, duration: int, source: Position, destination: Position, cell: Position):
    """
    Absolute time when the mover leaves `cell` toward the next square.
    Returns None if the piece stays on that cell (destination / never leaves).
    """
    path = path_cells(source, destination)
    steps = len(path) - 1
    for index, step_cell in enumerate(path):
        if step_cell != cell:
            continue
        # Destination square: piece arrives and stays — blocks forever for near-meet.
        if steps <= 0 or index >= steps:
            return None
        return start_time + int(round(duration * (index + 1) / float(steps)))
    return None


def shared_path_cells(source_a: Position, dest_a: Position, source_b: Position, dest_b: Position):
    """Cells that appear on both paths (meeting / crossing squares)."""
    cells_a = path_cells(source_a, dest_a)
    cells_b = set(path_cells(source_b, dest_b))
    return [cell for cell in cells_a if cell in cells_b]


def is_earlier_arrival(time_a, order_a, time_b, order_b) -> bool:
    """True if A arrives earlier than B (order breaks ties)."""
    if time_a != time_b:
        return time_a < time_b
    return order_a < order_b


def earlier_stop_along_path(source: Position, destination: Position, current_stop: Position, candidate: Position) -> Position:
    """Pick whichever stop is closer to source along the path."""
    path = path_cells(source, destination)
    try:
        current_index = path.index(current_stop)
    except ValueError:
        current_index = len(path) - 1
    try:
        candidate_index = path.index(candidate)
    except ValueError:
        return current_stop
    if candidate_index < current_index:
        return candidate
    return current_stop
