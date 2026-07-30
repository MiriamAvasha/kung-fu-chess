import os
from typing import Iterable, Optional, Tuple

import constants
from assets.piece_loader import PieceAssetLoader
from engine.results import GameSnapshot
from img import Img
from model.position import Position
from view import view_constants as vc
from view.motion_layout import (
    idle_pixel_position,
    jump_pixel_position,
    jump_progress,
    motion_pixel_position,
    motion_progress,
    motion_source_cells,
)

# Re-export colors so older imports (`from view.renderer import ...`) keep working.
SELECTED_BORDER_COLOR = vc.SELECTED_BORDER_COLOR
LEGAL_MOVE_DOT_COLOR = vc.LEGAL_MOVE_DOT_COLOR
GAME_OVER_BACKGROUND_COLOR = vc.GAME_OVER_BACKGROUND_COLOR
GAME_OVER_TEXT_COLOR = vc.GAME_OVER_TEXT_COLOR
LONG_REST_BACKGROUND_COLOR = vc.LONG_REST_BACKGROUND_COLOR
AIRBORNE_BACKGROUND_COLOR = vc.AIRBORNE_BACKGROUND_COLOR
JUMP_LABEL_COLOR = vc.JUMP_LABEL_COLOR


class Renderer:
    """Builds an image from a read-only GameSnapshot and live arbiter visuals."""

    def __init__(
        self,
        board_image_path: str = vc.BOARD_IMAGE_NAME,
        pieces_path: Optional[str] = None,
        cell_size: int = vc.DEFAULT_CELL_SIZE,
    ):
        self.board_image_path = board_image_path
        self.cell_size = cell_size
        self._board_cache = None
        self._board_cache_size = None

        if pieces_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pieces_path = os.path.join(base_dir, 'assets', vc.PIECES_DIR_NAME)
        self.piece_loader = PieceAssetLoader(pieces_path, cell_size=cell_size)

    def _cell_metrics(
        self,
        snapshot: GameSnapshot,
    ) -> Tuple[int, int, int]:
        if snapshot.board_width <= 0 or snapshot.board_height <= 0:
            raise ValueError('Snapshot board dimensions must be positive')
        return self.cell_size, self.cell_size, self.cell_size

    @staticmethod
    def _cell_bounds(col: int, row: int, cell_w: int, cell_h: int):
        """Exact pixel rectangle for one board cell: x, y, width, height."""
        return col * cell_w, row * cell_h, cell_w, cell_h

    def _board_canvas(self, canvas_size) -> Img:
        if self._board_cache is None or self._board_cache_size != canvas_size:
            self._board_cache = Img().read(
                self.board_image_path,
                size=canvas_size,
            )
            self._board_cache_size = canvas_size
        return self._board_cache.copy()

    def long_rest_duration_ms(
        self,
        token: str,
        state_name: str = vc.STATE_LONG_REST,
    ) -> int:
        color, kind = token[0], token[1]
        piece_assets = self.piece_loader.load(color, kind)
        rest_state = piece_assets.get_state(state_name)
        if rest_state is None or not rest_state.sprites:
            return 0
        return rest_state.animation_duration_ms

    def _piece_sprite(
        self,
        token: str,
        state_name: str = vc.STATE_IDLE,
        elapsed_ms: int = 0,
    ) -> Img:
        color, kind = token[0], token[1]
        piece_assets = self.piece_loader.load(color, kind)
        state = piece_assets.get_state(state_name)
        if state is None or not state.sprites:
            state = piece_assets.get_state(vc.STATE_IDLE)
        if state is None or not state.sprites:
            raise FileNotFoundError(
                f"No usable sprite for {token}. "
                f"Available states: {sorted(piece_assets.states.keys())}"
            )
        frame_index = int(max(0, elapsed_ms) / 1000.0 * state.frames_per_sec)
        if state.is_loop:
            frame_index %= len(state.sprites)
        else:
            frame_index = min(frame_index, len(state.sprites) - 1)
        return state.sprites[frame_index]

    def _draw_rest_fill(self, canvas, rest, current_time, cell_w, cell_h, alpha=None):
        remaining_ratio = rest.remaining_ratio(current_time)
        fill_height = max(0, min(cell_h, int(round(cell_h * remaining_ratio))))
        if fill_height <= 0:
            return
        x, y, width, height = self._cell_bounds(
            rest.col,
            rest.row,
            cell_w,
            cell_h,
        )
        fill_y = y + height - fill_height
        if alpha is None:
            canvas.fill_rectangle(
                x,
                fill_y,
                width,
                fill_height,
                vc.LONG_REST_BACKGROUND_COLOR,
            )
        else:
            canvas.fill_rectangle_alpha(
                x,
                fill_y,
                width,
                fill_height,
                vc.LONG_REST_BACKGROUND_COLOR,
                alpha=alpha,
            )

    def _draw_static_pieces(
        self,
        canvas,
        snapshot,
        moving_sources,
        jumping_cells,
        rests_by_cell,
        cell_w,
        cell_h,
        cell_size,
        current_time,
        visual_time_ms,
    ):
        for row, tokens in enumerate(snapshot.token_grid):
            for col, token in enumerate(tokens):
                if token == constants.EMPTY_CELL or len(token) != 2:
                    continue
                cell = Position(row, col)
                if cell in moving_sources or cell in jumping_cells:
                    continue
                rest = rests_by_cell.get(cell)
                if rest is not None:
                    elapsed_ms = max(0, current_time - rest.start_time)
                    piece_img = self._piece_sprite(
                        token,
                        state_name=vc.STATE_LONG_REST,
                        elapsed_ms=elapsed_ms,
                    )
                    x, y = col * cell_w, row * cell_h
                else:
                    piece_img = self._piece_sprite(
                        token,
                        state_name=vc.STATE_IDLE,
                        elapsed_ms=visual_time_ms,
                    )
                    x, y = idle_pixel_position(
                        row,
                        col,
                        visual_time_ms,
                        cell_size,
                    )
                piece_img.draw_on_clipped(
                    canvas,
                    int(round(x)),
                    int(round(y)),
                )

    def _draw_legal_destinations(
        self,
        canvas,
        snapshot,
        legal_destinations,
        cell_w,
        cell_h,
        cell_size,
    ):
        dot_radius = max(
            vc.LEGAL_DOT_MIN_RADIUS,
            cell_size // vc.LEGAL_DOT_RADIUS_DIVISOR,
        )
        for destination in legal_destinations:
            if not (
                0 <= destination.row < snapshot.board_height
                and 0 <= destination.col < snapshot.board_width
            ):
                continue
            canvas.draw_circle(
                destination.col * cell_w + cell_w // 2,
                destination.row * cell_h + cell_h // 2,
                dot_radius,
                vc.LEGAL_MOVE_DOT_COLOR,
            )

    def _draw_selection(self, canvas, snapshot, cell_w, cell_h, cell_size):
        selected = snapshot.selected_cell
        if selected is None:
            return
        if not (
            0 <= selected.row < snapshot.board_height
            and 0 <= selected.col < snapshot.board_width
        ):
            return
        canvas.draw_rectangle(
            selected.col * cell_w,
            selected.row * cell_h,
            cell_w,
            cell_h,
            vc.SELECTED_BORDER_COLOR,
            thickness=max(
                vc.SELECTION_BORDER_MIN_THICKNESS,
                cell_size // vc.SELECTION_BORDER_DIVISOR,
            ),
        )

    def _draw_motions(self, canvas, motions, current_time, cell_size):
        for motion in motions:
            x, y = motion_pixel_position(motion, current_time, cell_size)
            elapsed_ms = int(
                motion_progress(motion, current_time) * motion.duration
            )
            piece_img = self._piece_sprite(
                motion.piece_token,
                state_name=vc.STATE_MOVE,
                elapsed_ms=elapsed_ms,
            )
            piece_img.draw_on_clipped(
                canvas,
                int(round(x)),
                int(round(y)),
            )

    def _draw_jump_backgrounds(self, canvas, jumps, cell_w, cell_h):
        for jump in jumps:
            x, y, width, height = self._cell_bounds(
                jump.col,
                jump.row,
                cell_w,
                cell_h,
            )
            canvas.fill_rectangle(
                x,
                y,
                width,
                height,
                vc.AIRBORNE_BACKGROUND_COLOR,
            )

    def _draw_jumps(self, canvas, jumps, current_time, cell_w, cell_h, cell_size):
        for jump in jumps:
            piece_x, piece_y = jump_pixel_position(jump, current_time, cell_size)
            elapsed_ms = int(
                jump_progress(jump, current_time) * jump.duration
            )
            piece_img = self._piece_sprite(
                jump.piece_token,
                state_name=vc.STATE_JUMP,
                elapsed_ms=elapsed_ms,
            )
            piece_img.draw_on_clipped(
                canvas,
                int(round(piece_x)),
                int(round(piece_y)),
            )
            x, y, width, height = self._cell_bounds(
                jump.col,
                jump.row,
                cell_w,
                cell_h,
            )
            canvas.put_centered_text(
                vc.JUMP_LABEL,
                x + width // 2,
                y + height // 2,
                font_size=max(
                    vc.JUMP_LABEL_FONT_MIN,
                    cell_size / vc.JUMP_LABEL_FONT_DIVISOR,
                ),
                color=vc.JUMP_LABEL_COLOR,
                thickness=vc.JUMP_LABEL_THICKNESS,
            )

    def _draw_game_over(self, canvas, canvas_size, cell_size):
        canvas_width, canvas_height = canvas_size
        banner_height = max(
            cell_size,
            canvas_height // vc.GAME_OVER_BANNER_MIN_RATIO,
        )
        banner_y = (canvas_height - banner_height) // 2
        canvas.draw_rectangle(
            0,
            banner_y,
            canvas_width,
            banner_height,
            vc.GAME_OVER_BACKGROUND_COLOR,
            thickness=-1,
        )
        canvas.put_centered_text(
            vc.GAME_OVER_LABEL,
            canvas_width // 2,
            canvas_height // 2,
            font_size=max(
                vc.GAME_OVER_FONT_MIN,
                cell_size / vc.GAME_OVER_FONT_DIVISOR,
            ),
            color=vc.GAME_OVER_TEXT_COLOR,
            thickness=max(
                vc.GAME_OVER_THICKNESS_MIN,
                cell_size // vc.GAME_OVER_THICKNESS_DIVISOR,
            ),
        )

    def render(
        self,
        snapshot: GameSnapshot,
        legal_destinations: Iterable = (),
        active_motions: Iterable = (),
        active_jumps: Iterable = (),
        active_long_rests: Iterable = (),
        current_time: int = 0,
        visual_time_ms: int = 0,
    ) -> Img:
        cell_w, cell_h, cell_size = self._cell_metrics(snapshot)
        canvas_size = (
            snapshot.board_width * cell_w,
            snapshot.board_height * cell_h,
        )
        board_canvas = self._board_canvas(canvas_size)
        self.piece_loader.set_cell_size(cell_size)

        motions = tuple(active_motions)
        jumps = tuple(active_jumps)
        long_rests = tuple(active_long_rests)
        moving_sources = motion_source_cells(motions)
        jumping_cells = {
            Position(jump.row, jump.col)
            for jump in jumps
        }
        rests_by_cell = {
            Position(rest.row, rest.col): rest
            for rest in long_rests
        }

        for rest in long_rests:
            self._draw_rest_fill(
                board_canvas,
                rest,
                current_time,
                cell_w,
                cell_h,
            )
        self._draw_jump_backgrounds(board_canvas, jumps, cell_w, cell_h)

        self._draw_static_pieces(
            board_canvas,
            snapshot,
            moving_sources,
            jumping_cells,
            rests_by_cell,
            cell_w,
            cell_h,
            cell_size,
            current_time,
            visual_time_ms,
        )

        for rest in long_rests:
            self._draw_rest_fill(
                board_canvas,
                rest,
                current_time,
                cell_w,
                cell_h,
                alpha=vc.REST_OVERLAY_ALPHA,
            )

        self._draw_legal_destinations(
            board_canvas,
            snapshot,
            legal_destinations,
            cell_w,
            cell_h,
            cell_size,
        )
        self._draw_selection(
            board_canvas,
            snapshot,
            cell_w,
            cell_h,
            cell_size,
        )
        self._draw_motions(
            board_canvas,
            motions,
            current_time,
            cell_size,
        )
        self._draw_jumps(
            board_canvas,
            jumps,
            current_time,
            cell_w,
            cell_h,
            cell_size,
        )

        if snapshot.game_over:
            self._draw_game_over(board_canvas, canvas_size, cell_size)

        return board_canvas
