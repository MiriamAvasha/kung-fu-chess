import math

import constants

STATE_IDLE = 'idle'
STATE_MOVE = 'move'
STATE_JUMP = 'jump'
STATE_SHORT_REST = 'short_rest'
STATE_LONG_REST = 'long_rest'

EVENT_START_MOVE = 'start_move'
EVENT_START_JUMP = 'start_jump'
EVENT_FINISHED = 'finished'

# Explicit state table: (current_state, event) -> next_state
TRANSITIONS = {
    (STATE_IDLE, EVENT_START_MOVE): STATE_MOVE,
    (STATE_IDLE, EVENT_START_JUMP): STATE_JUMP,
    (STATE_MOVE, EVENT_FINISHED): STATE_LONG_REST,
    (STATE_JUMP, EVENT_FINISHED): STATE_SHORT_REST,
    (STATE_SHORT_REST, EVENT_FINISHED): STATE_IDLE,
    (STATE_LONG_REST, EVENT_FINISHED): STATE_IDLE,
}

REST_STATES = {STATE_SHORT_REST, STATE_LONG_REST}
BUSY_STATES = {STATE_MOVE, STATE_JUMP, STATE_SHORT_REST, STATE_LONG_REST}

BREATH_AMPLITUDE_PX = 3.0
BREATH_PERIOD_MS = 1400.0
JUMP_HOP_PX = 28.0


class PieceStateMachine:
    def __init__(self, assets):
        self.assets = assets
        self.state = STATE_IDLE
        self.elapsed_ms = 0
        self.duration_ms = 0
        self.idle_ms = 0
        self.from_pos = None
        self.to_pos = None
        self.pixel_x = 0.0
        self.pixel_y = 0.0
        self.base_pixel_x = 0.0
        self.base_pixel_y = 0.0
        self._on_arrived = None

    def can_transition(self, event: str) -> bool:
        return (self.state, event) in TRANSITIONS

    def transition(self, event: str) -> bool:
        """Apply one row from TRANSITIONS. Returns False if the event is illegal now."""
        next_state = TRANSITIONS.get((self.state, event))
        if next_state is None:
            return False
        self.state = next_state
        return True

    @property
    def is_idle(self) -> bool:
        return self.state == STATE_IDLE

    @property
    def is_resting(self) -> bool:
        return self.state in REST_STATES

    @property
    def is_jumping(self) -> bool:
        return self.state == STATE_JUMP

    @property
    def is_busy(self) -> bool:
        return self.state in BUSY_STATES

    @property
    def rest_remaining_ms(self) -> int:
        if not self.is_resting:
            return 0
        return max(0, self.duration_ms - self.elapsed_ms)

    @property
    def rest_progress(self) -> float:
        if not self.is_resting or self.duration_ms <= 0:
            return 0.0
        return min(1.0, self.elapsed_ms / float(self.duration_ms))

    def place_at_cell(self, row: int, col: int, cell_size: int):
        self.base_pixel_x = col * cell_size
        self.base_pixel_y = row * cell_size
        self.pixel_x = self.base_pixel_x
        self.pixel_y = self.base_pixel_y

    def abort_to_cell(self, cell, cell_size: int):
        """Stop mid-move and stay on the last safe square (before a collision)."""
        self._on_arrived = None
        self.state = STATE_IDLE
        self.elapsed_ms = 0
        self.duration_ms = 0
        self.idle_ms = 0
        self.from_pos = None
        self.to_pos = None
        self.place_at_cell(cell.row, cell.col, cell_size)

    def start_move(self, from_pos, to_pos, cell_size: int, on_arrived=None):
        if not self.can_transition(EVENT_START_MOVE):
            return False
        state_assets = self.assets.get_state(STATE_MOVE)
        if state_assets is None:
            return False
        cells = max(abs(to_pos.row - from_pos.row), abs(to_pos.col - from_pos.col), 1)
        speed = state_assets.speed_m_per_sec or 1.0
        if not self.transition(EVENT_START_MOVE):
            return False
        self.elapsed_ms = 0
        self.idle_ms = 0
        self.duration_ms = int(round(cells / speed * 1000))
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.place_at_cell(from_pos.row, from_pos.col, cell_size)
        self._on_arrived = on_arrived
        return True

    def start_jump(self, cell, cell_size: int, on_arrived=None):
        if not self.can_transition(EVENT_START_JUMP):
            return False
        state_assets = self.assets.get_state(STATE_JUMP)
        if state_assets is None:
            return False
        if not self.transition(EVENT_START_JUMP):
            return False
        self.elapsed_ms = 0
        self.idle_ms = 0
        # Match VPL: jump lasts JUMP_DURATION ms on the same logical cell.
        self.duration_ms = constants.JUMP_DURATION
        self.from_pos = cell
        self.to_pos = cell
        self.place_at_cell(cell.row, cell.col, cell_size)
        self._on_arrived = on_arrived
        return True

    def tick(self, dt_ms: int, cell_size: int):
        if self.state == STATE_IDLE:
            self.idle_ms += dt_ms
            bob = math.sin(self.idle_ms / BREATH_PERIOD_MS * math.pi * 2.0) * BREATH_AMPLITUDE_PX
            self.pixel_x = self.base_pixel_x
            self.pixel_y = self.base_pixel_y + bob
            return

        self.elapsed_ms += dt_ms
        progress = 1.0 if self.duration_ms <= 0 else min(1.0, self.elapsed_ms / float(self.duration_ms))

        if self.state == STATE_JUMP and self.from_pos is not None:
            self.base_pixel_x = self.from_pos.col * cell_size
            self.base_pixel_y = self.from_pos.row * cell_size
            hop = math.sin(progress * math.pi) * JUMP_HOP_PX
            self.pixel_x = self.base_pixel_x
            self.pixel_y = self.base_pixel_y - hop
        elif self.state == STATE_MOVE and self.from_pos and self.to_pos:
            start_x = self.from_pos.col * cell_size
            start_y = self.from_pos.row * cell_size
            end_x = self.to_pos.col * cell_size
            end_y = self.to_pos.row * cell_size
            self.base_pixel_x = start_x + (end_x - start_x) * progress
            self.base_pixel_y = start_y + (end_y - start_y) * progress
            self.pixel_x = self.base_pixel_x
            self.pixel_y = self.base_pixel_y

        if self.elapsed_ms >= self.duration_ms:
            self._finish_state(cell_size)

    def _finish_state(self, cell_size: int):
        previous = self.state

        if previous in (STATE_MOVE, STATE_JUMP) and self.to_pos is not None:
            land_at = self.to_pos
            if self._on_arrived is not None:
                # Callback may return a Position to bounce back (e.g. same-color collision).
                result = self._on_arrived(self.to_pos)
                self._on_arrived = None
                if result is not None:
                    land_at = result
            self.place_at_cell(land_at.row, land_at.col, cell_size)

        if not self.transition(EVENT_FINISHED):
            self.state = STATE_IDLE
            self.elapsed_ms = 0
            self.duration_ms = 0
            self.idle_ms = 0
            self.from_pos = None
            self.to_pos = None
            return

        if self.state in REST_STATES:
            rest_assets = self.assets.get_state(self.state)
            self.elapsed_ms = 0
            self.duration_ms = rest_assets.animation_duration_ms if rest_assets else 500
            self.from_pos = None
            self.to_pos = None
            return

        # Entered idle via TRANSITIONS
        self.elapsed_ms = 0
        self.duration_ms = 0
        self.idle_ms = 0
        self.from_pos = None
        self.to_pos = None

    def current_sprite(self):
        state_assets = self.assets.get_state(self.state)
        if self.state == STATE_IDLE:
            idle = self.assets.get_state(STATE_IDLE)
            if idle is None or not idle.sprites:
                return None
            fps = idle.frames_per_sec or 1.0
            frame_index = int(self.idle_ms / 1000.0 * fps) % len(idle.sprites)
            return idle.sprites[frame_index]
        if state_assets is None or not state_assets.sprites:
            idle = self.assets.get_state(STATE_IDLE)
            if idle and idle.sprites:
                return idle.sprites[0]
            return None
        fps = state_assets.frames_per_sec or 1.0
        frame_index = int(self.elapsed_ms / 1000.0 * fps)
        if state_assets.is_loop:
            frame_index %= len(state_assets.sprites)
        else:
            frame_index = min(frame_index, len(state_assets.sprites) - 1)
        return state_assets.sprites[frame_index]
