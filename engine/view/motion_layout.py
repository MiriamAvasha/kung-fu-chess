import math

from model.position import Position
from view import view_constants as vc


def motion_progress(motion, current_time: int) -> float:
    if motion.duration <= 0:
        return 1.0
    elapsed = current_time - motion.start_time
    return max(0.0, min(1.0, elapsed / float(motion.duration)))


def motion_pixel_position(motion, current_time: int, cell_size: int):
    progress = motion_progress(motion, current_time)
    start_x = motion.from_col * cell_size
    start_y = motion.from_row * cell_size
    end_x = motion.to_col * cell_size
    end_y = motion.to_row * cell_size
    return (
        start_x + (end_x - start_x) * progress,
        start_y + (end_y - start_y) * progress,
    )


def motion_source_cells(motions):
    return {
        Position(motion.from_row, motion.from_col)
        for motion in motions
    }


def idle_pixel_position(
    row: int,
    col: int,
    visual_time_ms: int,
    cell_size: int,
):
    phase = (
        row * vc.IDLE_BOB_PHASE_ROW
        + col * vc.IDLE_BOB_PHASE_COL
    ) * vc.IDLE_BOB_PHASE_SCALE
    angle = (
        visual_time_ms / vc.IDLE_BOB_PERIOD_MS * math.pi * 2.0
        + phase
    )
    offset_y = math.sin(angle) * max(1.0, cell_size * vc.IDLE_BOB_RATIO)
    return col * cell_size, row * cell_size + offset_y


def jump_progress(jump, current_time: int) -> float:
    if jump.duration <= 0:
        return 1.0
    elapsed = current_time - jump.start_time
    return max(0.0, min(1.0, elapsed / float(jump.duration)))


def jump_pixel_position(jump, current_time: int, cell_size: int):
    progress = jump_progress(jump, current_time)
    hop_height = math.sin(progress * math.pi) * cell_size * vc.JUMP_HEIGHT_RATIO
    return (
        jump.col * cell_size,
        jump.row * cell_size - hop_height,
    )
