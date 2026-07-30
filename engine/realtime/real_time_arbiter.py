from model.game_state import GameState
from model.position import Position
from realtime.jump import Jump
from realtime.long_rest import LongRest
from realtime.motion import Motion
from rules.path_utils import (
    earlier_stop_along_path,
    is_earlier_arrival,
    last_square_before,
    path_cells,
    shared_path_cells,
    time_to_leave_cell,
    time_to_reach_cell,
)
from rules.promotion import DEFAULT_PROMOTION_SERVICE


def _get_route_columns(from_col: int, to_col: int) -> set:
    if from_col == to_col:
        return set()
    lo, hi = min(from_col, to_col), max(from_col, to_col)
    return set(range(lo + 1, hi + 1))


def _get_route_rows(from_row: int, to_row: int) -> set:
    if from_row == to_row:
        return set()
    lo, hi = min(from_row, to_row), max(from_row, to_row)
    return set(range(lo + 1, hi + 1))


def _is_mutual_swap(motion: Motion, other: Motion) -> bool:
    return (
        (motion.to_row, motion.to_col) == (other.from_row, other.from_col)
        and (other.to_row, other.to_col) == (motion.from_row, motion.from_col)
    )


def _is_mutual_enemy_collision(from_row, from_col, to_row, to_col, piece_color, other: Motion) -> bool:
    if other.piece_token[0] == piece_color:
        return False
    return (
        (to_row, to_col) == (other.from_row, other.from_col)
        and (other.to_row, other.to_col) == (from_row, from_col)
    )


def _motion_source(motion: Motion) -> Position:
    return Position(motion.from_row, motion.from_col)


def _motion_dest(motion: Motion) -> Position:
    return Position(motion.to_row, motion.to_col)


def _motion_original_dest(motion: Motion) -> Position:
    return Position(motion.original_to_row, motion.original_to_col)


class RealTimeArbiter:
    def __init__(self, long_rest_duration_provider=None):
        self.current_time = 0
        self.active_motions = {}
        self.active_jumps = {}
        self.active_long_rests = {}
        self._long_rest_duration_provider = long_rest_duration_provider
        self._move_order = 0

    def set_long_rest_duration_provider(self, provider):
        """provider(token, state_name) -> duration_ms"""
        self._long_rest_duration_provider = provider

    def is_piece_resting(self, piece_id: int) -> bool:
        return piece_id in self.active_long_rests

    def _rest_duration(self, token: str, state_name: str) -> int:
        if self._long_rest_duration_provider is None:
            return 0
        try:
            return int(self._long_rest_duration_provider(token, state_name))
        except TypeError:
            # Backward-compatible providers that accept only the token.
            return int(self._long_rest_duration_provider(token))

    def _start_rest(
        self,
        piece_id: int,
        piece_token: str,
        position: Position,
        state_name: str,
    ):
        duration = self._rest_duration(piece_token, state_name)
        if piece_id <= 0 or duration <= 0:
            return
        self.active_long_rests[piece_id] = LongRest(
            piece_id,
            piece_token,
            position.row,
            position.col,
            self.current_time,
            duration,
        )

    def _start_rest_for_piece(self, piece, position: Position, state_name: str):
        if piece is None:
            return
        self._start_rest(piece.id, piece.token, position, state_name)

    def _expire_due_long_rests(self):
        expired = [
            piece_id
            for piece_id, rest in self.active_long_rests.items()
            if self.current_time >= rest.end_time
        ]
        for piece_id in expired:
            del self.active_long_rests[piece_id]

    def has_active_motion_from(self, row: int, col: int) -> bool:
        return (row, col) in self.active_motions

    def has_any_active_motion(self) -> bool:
        return len(self.active_motions) > 0

    def advance_time(self, game_state: GameState, ms: int):
        self.current_time += ms
        self._resolve_same_color_path_blocks(game_state)
        self._complete_due_motions(game_state)
        self._expire_due_jumps()
        self._expire_due_long_rests()
        self._resolve_same_color_path_blocks(game_state)

    def start_motion(self, game_state: GameState, from_row, from_col, to_row, to_col, piece_token, duration):
        self._move_order += 1
        piece = game_state.board.piece_at(Position(from_row, from_col))
        piece_id = piece.id if piece else 0
        self.active_motions[(from_row, from_col)] = Motion(
            piece_id, piece_token, from_row, from_col, to_row, to_col,
            self.current_time, duration, self._move_order
        )
        self._resolve_same_color_path_blocks(game_state)

    def start_jump(self, game_state: GameState, row: int, col: int, piece_token: str):
        piece = game_state.board.piece_at(Position(row, col))
        piece_id = piece.id if piece is not None else 0
        self.active_jumps[(row, col)] = Jump(
            piece_id,
            piece_token,
            row,
            col,
            self.current_time,
        )

    def has_opposite_color_route_conflict(
        self, game_state: GameState, piece_color: str,
        from_row: int, from_col: int, to_row: int, to_col: int
    ) -> bool:
        for active in self.active_motions.values():
            if active.piece_token[0] == piece_color:
                continue
            if _is_mutual_enemy_collision(from_row, from_col, to_row, to_col, piece_color, active):
                continue
            new_cols = _get_route_columns(from_col, to_col)
            new_rows = _get_route_rows(from_row, to_row)
            active_cols = _get_route_columns(active.from_col, active.to_col)
            active_rows = _get_route_rows(active.from_row, active.to_row)
            same_row_horizontal = (
                from_row == to_row
                and active.from_row == active.to_row
                and from_row == active.from_row
            )
            same_col_vertical = (
                from_col == to_col
                and active.from_col == active.to_col
                and from_col == active.from_col
            )
            if same_row_horizontal and new_cols & active_cols:
                return True
            if same_col_vertical and new_rows & active_rows:
                return True
        return False

    def _is_airborne_at(self, row: int, col: int, at_time: int = None):
        jump = self.active_jumps.get((row, col))
        checked_time = self.current_time if at_time is None else at_time
        if jump and jump.start_time <= checked_time <= jump.end_time:
            return jump
        return None

    def _expire_due_jumps(self):
        expired = [
            (key, jump)
            for key, jump in self.active_jumps.items()
            if self.current_time > jump.end_time
        ]
        for key, jump in expired:
            del self.active_jumps[key]
            self._start_rest(
                jump.piece_id,
                jump.piece_token,
                Position(jump.row, jump.col),
                'short_rest',
            )

    def _truncate_motion_to(self, motion: Motion, stop: Position):
        source = _motion_source(motion)
        original_dest = _motion_original_dest(motion)
        path = path_cells(source, original_dest)
        try:
            stop_index = path.index(stop)
        except ValueError:
            return
        steps = len(path) - 1
        if steps <= 0:
            return
        motion.to_row = stop.row
        motion.to_col = stop.col
        motion.duration = int(round(motion.original_duration * stop_index / float(steps)))

    def _resolve_same_color_path_blocks(self, game_state: GameState):
        """
        Same-color near-meet: whoever reaches a shared path cell later stops
        on the square before that cell. Earlier piece continues.
        """
        motions = list(self.active_motions.values())
        for i in range(len(motions)):
            for j in range(i + 1, len(motions)):
                a = motions[i]
                b = motions[j]
                if a.piece_token[0] != b.piece_token[0]:
                    continue
                src_a = _motion_source(a)
                src_b = _motion_source(b)
                orig_a = _motion_original_dest(a)
                orig_b = _motion_original_dest(b)
                for cell in shared_path_cells(src_a, orig_a, src_b, orig_b):
                    # Ignore pure start-square overlap.
                    if cell == src_a or cell == src_b:
                        continue
                    t_a = time_to_reach_cell(
                        a.start_time, a.original_duration, src_a, orig_a, cell
                    )
                    t_b = time_to_reach_cell(
                        b.start_time, b.original_duration, src_b, orig_b, cell
                    )
                    if t_a is None or t_b is None:
                        continue
                    if is_earlier_arrival(t_a, a.order, t_b, b.order):
                        earlier, later = a, b
                        earlier_src, earlier_orig = src_a, orig_a
                        later_src, later_orig = src_b, orig_b
                        t_later = t_b
                    else:
                        earlier, later = b, a
                        earlier_src, earlier_orig = src_b, orig_b
                        later_src, later_orig = src_a, orig_a
                        t_later = t_a
                    # Near-meet if later arrives before earlier leaves (None = stays forever).
                    leave = time_to_leave_cell(
                        earlier.start_time, earlier.original_duration,
                        earlier_src, earlier_orig, cell,
                    )
                    if leave is not None and t_later > leave:
                        continue
                    stop = last_square_before(later_src, later_orig, cell)
                    current = _motion_dest(later)
                    better = earlier_stop_along_path(later_src, later_orig, current, stop)
                    if better != current:
                        self._truncate_motion_to(later, better)

        self._resolve_static_path_blocks(game_state)

    def _resolve_static_path_blocks(self, game_state: GameState):
        """Block movers that would pass through a piece already sitting on their path."""
        moving_ids = {motion.piece_id for motion in self.active_motions.values()}
        for motion in list(self.active_motions.values()):
            source = _motion_source(motion)
            original = _motion_original_dest(motion)
            path = path_cells(source, original)
            for cell in path[1:]:
                occupant = game_state.board.piece_at(cell)
                if occupant is None or occupant.id in moving_ids:
                    continue
                if occupant.color == motion.piece_token[0]:
                    # Ally already on path — stop before that square.
                    stop = last_square_before(source, original, cell)
                else:
                    # Enemy on an intermediate square — cannot pass through.
                    if cell == original:
                        continue
                    stop = last_square_before(source, original, cell)
                current = _motion_dest(motion)
                better = earlier_stop_along_path(source, original, current, stop)
                if better != current:
                    self._truncate_motion_to(motion, better)

    def _stop_at(self, game_state: GameState, motion: Motion, stop: Position):
        source = _motion_source(motion)
        if stop == source:
            return
        if game_state.board.piece_at(stop) is not None:
            return
        moving_piece = game_state.board.piece_at(source)
        if moving_piece is None:
            return
        new_kind = DEFAULT_PROMOTION_SERVICE.resolve(game_state.board, moving_piece, stop)
        game_state.board.move_piece(source, stop, new_kind)
        self._start_rest_for_piece(moving_piece, stop, 'long_rest')

    def _apply_motion(self, game_state: GameState, motion: Motion) -> bool:
        airborne = self._is_airborne_at(
            motion.to_row,
            motion.to_col,
            at_time=motion.arrival_time,
        )
        if airborne and airborne.piece_token[0] != motion.piece_token[0]:
            # Airborne defender still eats the attacker.
            defender = game_state.board.piece_at(
                Position(motion.to_row, motion.to_col)
            )
            game_state.board.remove_piece(Position(motion.from_row, motion.from_col))
            if motion.piece_token[1] == 'K':
                game_state.game_over = True
                self.active_motions.clear()
                self.active_jumps.clear()
                self.active_long_rests.clear()
                return True
            self._start_rest_for_piece(
                defender,
                Position(motion.to_row, motion.to_col),
                'long_rest',
            )
            return False

        source = _motion_source(motion)
        destination = _motion_dest(motion)
        occupant = game_state.board.piece_at(destination)

        # Same-color: later arriver never captures — stop before the meeting cell.
        if occupant is not None and occupant.color == motion.piece_token[0]:
            stop = last_square_before(source, destination, destination)
            self._stop_at(game_state, motion, stop)
            return False

        moving_piece = game_state.board.piece_at(source)
        if moving_piece is None:
            return False

        # Opposite-color: this mover arrived at destination now → eats whoever is there
        # (idle piece, or earlier arriver). Later always eats earlier.
        if occupant is not None:
            self.active_long_rests.pop(occupant.id, None)
            game_state.board.remove_piece(destination)
            self.active_motions.pop((destination.row, destination.col), None)

        new_kind = DEFAULT_PROMOTION_SERVICE.resolve(game_state.board, moving_piece, destination)
        game_state.board.move_piece(source, destination, new_kind)

        if occupant is not None and occupant.kind == 'K':
            game_state.game_over = True
            self.active_motions.clear()
            self.active_long_rests.clear()
            return True
        # After every successful landing the piece rests (asset FSM: move → long_rest).
        self._start_rest_for_piece(moving_piece, destination, 'long_rest')
        return False

    def _complete_due_motions(self, game_state: GameState):
        due_motions = [
            self.active_motions.pop(key)
            for key, motion in list(self.active_motions.items())
            if self.current_time >= motion.arrival_time
        ]
        if not due_motions:
            return

        # Earlier arrival first; later movers applied after so they can eat.
        due_motions.sort(key=lambda move: (move.arrival_time, move.order))
        cancelled = set()

        for i, motion in enumerate(due_motions):
            if i in cancelled:
                continue
            for j in range(i + 1, len(due_motions)):
                if j in cancelled:
                    continue
                other = due_motions[j]
                if motion.piece_token[0] == other.piece_token[0]:
                    continue
                # Opposite-color head-on swap: later eats earlier.
                # Cancel earlier so they stay on their square; later captures them there.
                if _is_mutual_swap(motion, other):
                    cancelled.add(i)

        for i, motion in enumerate(due_motions):
            if game_state.game_over:
                break
            if i not in cancelled:
                self._apply_motion(game_state, motion)

    def complete_pending(self, game_state: GameState):
        self._resolve_same_color_path_blocks(game_state)
        self._complete_due_motions(game_state)
        self._expire_due_jumps()
        self._expire_due_long_rests()
        self._resolve_same_color_path_blocks(game_state)
