import json

import cv2
import numpy as np
import pytest

from engine.results import GameSnapshot
from img import Img
from model.position import Position
from realtime.jump import Jump
from realtime.long_rest import LongRest
from realtime.motion import Motion
from view.view_constants import (
    AIRBORNE_BACKGROUND_COLOR,
    GAME_OVER_BACKGROUND_COLOR,
    LEGAL_MOVE_DOT_COLOR,
    LONG_REST_BACKGROUND_COLOR,
    SELECTED_BORDER_COLOR,
)
from view.renderer import Renderer



def _write_image(path, width, height, color):
    image = np.zeros((height, width, 4), dtype=np.uint8)
    image[:, :] = color
    assert cv2.imwrite(str(path), image)


def _write_idle_piece(pieces_root, token):
    idle_path = pieces_root / token / 'states' / 'idle'
    sprites_path = idle_path / 'sprites'
    sprites_path.mkdir(parents=True)
    (idle_path / 'config.json').write_text(
        json.dumps({
            'physics': {},
            'graphics': {'frames_per_sec': 1, 'is_loop': True},
        }),
        encoding='utf-8',
    )
    _write_image(sprites_path / '1.png', 10, 10, (10, 20, 30, 255))


def _write_move_piece(pieces_root, token):
    move_path = pieces_root / token / 'states' / 'move'
    sprites_path = move_path / 'sprites'
    sprites_path.mkdir(parents=True)
    (move_path / 'config.json').write_text(
        json.dumps({
            'physics': {'speed_m_per_sec': 1},
            'graphics': {'frames_per_sec': 1, 'is_loop': True},
        }),
        encoding='utf-8',
    )
    _write_image(sprites_path / '1.png', 10, 10, (50, 60, 70, 255))


def _write_jump_piece(pieces_root, token):
    jump_path = pieces_root / token / 'states' / 'jump'
    sprites_path = jump_path / 'sprites'
    sprites_path.mkdir(parents=True)
    (jump_path / 'config.json').write_text(
        json.dumps({
            'physics': {},
            'graphics': {'frames_per_sec': 1, 'is_loop': False},
        }),
        encoding='utf-8',
    )
    _write_image(sprites_path / '1.png', 10, 10, (80, 90, 100, 255))


def _write_animated_idle_piece(pieces_root, token):
    idle_path = pieces_root / token / 'states' / 'idle'
    sprites_path = idle_path / 'sprites'
    sprites_path.mkdir(parents=True)
    (idle_path / 'config.json').write_text(
        json.dumps({
            'physics': {},
            'graphics': {'frames_per_sec': 2, 'is_loop': True},
        }),
        encoding='utf-8',
    )
    _write_image(sprites_path / '1.png', 10, 10, (10, 20, 30, 255))
    _write_image(sprites_path / '2.png', 10, 10, (110, 120, 130, 255))


def _write_long_rest_piece(pieces_root, token):
    rest_path = pieces_root / token / 'states' / 'long_rest'
    sprites_path = rest_path / 'sprites'
    sprites_path.mkdir(parents=True)
    (rest_path / 'config.json').write_text(
        json.dumps({
            'physics': {},
            'graphics': {'frames_per_sec': 2, 'is_loop': False},
        }),
        encoding='utf-8',
    )
    for frame in range(1, 6):
        _write_image(
            sprites_path / f'{frame}.png',
            10,
            10,
            (140, 150, 160, 255),
        )


class TestRenderer:
    def test_render_uses_snapshot_dimensions_and_tokens(self, tmp_path):
        board_path = tmp_path / 'board.png'
        pieces_root = tmp_path / 'pieces'
        _write_image(board_path, 37, 31, (0, 0, 0, 255))
        _write_idle_piece(pieces_root, 'wK')

        renderer = Renderer(str(board_path), str(pieces_root), cell_size=10)
        snapshot = GameSnapshot(
            2,
            2,
            [['wK', '.'], ['.', '.']],
            game_over=False,
        )

        result = renderer.render(snapshot)

        assert isinstance(result, Img)
        assert result.img.shape == (20, 20, 4)
        assert tuple(result.img[5, 5]) == (10, 20, 30, 255)
        assert tuple(result.img[15, 15]) == (0, 0, 0, 255)

    def test_render_marks_selected_cell(self, tmp_path):
        board_path = tmp_path / 'board.png'
        _write_image(board_path, 20, 20, (0, 0, 0, 255))
        renderer = Renderer(
            str(board_path),
            str(tmp_path / 'pieces'),
            cell_size=10,
        )
        snapshot = GameSnapshot(
            2,
            2,
            [['.', '.'], ['.', '.']],
            game_over=False,
            selected_cell=Position(0, 1),
        )

        result = renderer.render(snapshot)

        assert tuple(result.img[0, 10]) == SELECTED_BORDER_COLOR
        assert tuple(result.img[5, 15]) == (0, 0, 0, 255)

    def test_render_marks_legal_destinations_with_center_dots(self, tmp_path):
        board_path = tmp_path / 'board.png'
        _write_image(board_path, 20, 20, (0, 0, 0, 255))
        renderer = Renderer(
            str(board_path),
            str(tmp_path / 'pieces'),
            cell_size=10,
        )
        snapshot = GameSnapshot(
            2,
            2,
            [['.', '.'], ['.', '.']],
            game_over=False,
        )

        result = renderer.render(snapshot, {Position(1, 0)})

        assert tuple(result.img[15, 5]) == LEGAL_MOVE_DOT_COLOR
        assert tuple(result.img[5, 15]) == (0, 0, 0, 255)

    def test_render_interpolates_active_motion_without_drawing_source_twice(
        self,
        tmp_path,
    ):
        board_path = tmp_path / 'board.png'
        pieces_root = tmp_path / 'pieces'
        _write_image(board_path, 30, 10, (0, 0, 0, 255))
        _write_idle_piece(pieces_root, 'wR')
        _write_move_piece(pieces_root, 'wR')
        renderer = Renderer(str(board_path), str(pieces_root), cell_size=10)
        snapshot = GameSnapshot(
            3,
            1,
            [['wR', '.', '.']],
            game_over=False,
        )
        motion = Motion(1, 'wR', 0, 0, 0, 2, 0, 1000, 1)

        result = renderer.render(
            snapshot,
            active_motions=[motion],
            current_time=500,
        )

        assert tuple(result.img[5, 5]) == (0, 0, 0, 255)
        assert tuple(result.img[5, 15]) == (50, 60, 70, 255)

    def test_render_animates_idle_sprite_frames(self, tmp_path):
        board_path = tmp_path / 'board.png'
        pieces_root = tmp_path / 'pieces'
        _write_image(board_path, 20, 20, (0, 0, 0, 255))
        _write_animated_idle_piece(pieces_root, 'wK')
        renderer = Renderer(str(board_path), str(pieces_root), cell_size=20)
        snapshot = GameSnapshot(
            1,
            1,
            [['wK']],
            game_over=False,
        )

        result = renderer.render(snapshot, visual_time_ms=500)

        assert tuple(result.img[10, 10]) == (110, 120, 130, 255)

    def test_render_draws_airborne_piece_above_its_cell(self, tmp_path):
        board_path = tmp_path / 'board.png'
        pieces_root = tmp_path / 'pieces'
        _write_image(board_path, 20, 40, (0, 0, 0, 255))
        _write_idle_piece(pieces_root, 'wK')
        _write_jump_piece(pieces_root, 'wK')
        renderer = Renderer(str(board_path), str(pieces_root), cell_size=20)
        snapshot = GameSnapshot(
            1,
            2,
            [['.'], ['wK']],
            game_over=False,
        )
        jump = Jump(1, 'wK', row=1, col=0, start_time=0)

        result = renderer.render(
            snapshot,
            active_jumps=[jump],
            current_time=500,
        )

        assert tuple(result.img[15, 10][:3]) == (80, 90, 100)
        # Light-blue cell background remains visible under the hop.
        assert result.img[38, 10][0] > 150

    def test_render_shrinks_yellow_background_during_long_rest(self, tmp_path):
        board_path = tmp_path / 'board.png'
        _write_image(board_path, 10, 10, (0, 0, 0, 255))
        renderer = Renderer(
            str(board_path),
            str(tmp_path / 'pieces'),
            cell_size=10,
        )
        snapshot = GameSnapshot(1, 1, [['.']], game_over=False)
        rest = LongRest(1, 'wR', 0, 0, start_time=0, duration=1000)

        result = renderer.render(
            snapshot,
            active_long_rests=[rest],
            current_time=500,
        )

        # Top of cell stays dark; bottom half is bright yellow (BGR).
        assert tuple(result.img[3, 5][:3]) == (0, 0, 0)
        assert tuple(result.img[7, 5][:3]) == (160, 255, 255)

    def test_long_rest_duration_comes_from_asset_configuration(self, tmp_path):
        board_path = tmp_path / 'board.png'
        pieces_root = tmp_path / 'pieces'
        _write_image(board_path, 10, 10, (0, 0, 0, 255))
        _write_long_rest_piece(pieces_root, 'wK')
        renderer = Renderer(str(board_path), str(pieces_root), cell_size=10)

        assert renderer.long_rest_duration_ms('wK') == 2500

    def test_render_writes_game_over_banner(self, tmp_path):
        board_path = tmp_path / 'board.png'
        _write_image(board_path, 100, 100, (0, 0, 0, 255))
        renderer = Renderer(
            str(board_path),
            str(tmp_path / 'pieces'),
            cell_size=50,
        )
        snapshot = GameSnapshot(
            2,
            2,
            [['.', '.'], ['.', '.']],
            game_over=True,
        )

        result = renderer.render(snapshot)

        assert tuple(result.img[30, 1]) == GAME_OVER_BACKGROUND_COLOR

    def test_render_rejects_empty_board_dimensions(self, tmp_path):
        board_path = tmp_path / 'board.png'
        _write_image(board_path, 20, 20, (0, 0, 0, 255))
        renderer = Renderer(str(board_path), str(tmp_path / 'pieces'))
        snapshot = GameSnapshot(0, 0, [], game_over=False)

        with pytest.raises(ValueError, match='dimensions must be positive'):
            renderer.render(snapshot)
