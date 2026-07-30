"""Graphical entry point for the online client.

The original local board remains available through ``run_local_game``.
"""

import asyncio
import os

from client.gui.app import main as run_online_client
from engine.game_factory import build_engine
from engine.game_engine import GameEngine
from input.controller import Controller
from rules.piece_rules import PIECE_RULES
from view import view_constants as vc
from view.image_view import ImageView
from view.renderer import Renderer


def _legal_destinations(engine: GameEngine, selected_cell):
    if selected_cell is None:
        return set()
    piece = engine.game_state.board.piece_at(selected_cell)
    if piece is None:
        return set()
    rule = PIECE_RULES.get(piece.kind)
    if rule is None:
        return set()
    return rule.legal_destinations(engine.game_state.board, piece)


def _has_timed_action(engine: GameEngine) -> bool:
    return (
        engine.arbiter.has_any_active_motion()
        or bool(engine.arbiter.active_jumps)
        or bool(engine.arbiter.active_long_rests)
    )


def run_local_game():
    """Run the original single-process board demo."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    board_path = os.path.join(base_dir, 'assets', vc.BOARD_IMAGE_NAME)
    pieces_path = os.path.join(base_dir, 'assets', vc.PIECES_DIR_NAME)

    engine = build_engine()
    renderer = Renderer(board_path, pieces_path)
    engine.arbiter.set_long_rest_duration_provider(
        renderer.long_rest_duration_ms
    )
    controller = Controller(engine, cell_size=renderer.cell_size)
    image_view = ImageView()
    visual_time_ms = [0]

    def render_current_state():
        return renderer.render(
            engine.snapshot(controller.selected_cell),
            _legal_destinations(engine, controller.selected_cell),
            active_motions=engine.arbiter.active_motions.values(),
            active_jumps=engine.arbiter.active_jumps.values(),
            active_long_rests=engine.arbiter.active_long_rests.values(),
            current_time=engine.arbiter.current_time,
            visual_time_ms=visual_time_ms[0],
        )

    def handle_click(x: int, y: int):
        controller.click(x, y)

    def advance_animation(elapsed_ms: int):
        visual_time_ms[0] += elapsed_ms
        if elapsed_ms > 0 and _has_timed_action(engine):
            engine.wait(elapsed_ms)

    def is_animating():
        return not engine.game_state.game_over

    image_view.run(
        render_current_state,
        handle_click,
        advance_animation,
        is_animating,
    )


def main():
    """Launch the server-connected graphical client."""
    asyncio.run(run_online_client())


if __name__ == '__main__':
    main()
