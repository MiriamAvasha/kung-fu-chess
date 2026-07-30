import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.game_engine import GameEngine
from input.controller import Controller
from model.board import board_from_token_rows
from model.game_state import GameState
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import RuleEngine
import constants


def make_board(rows):
    """Build a board from token rows. Use '.' for empty."""
    return board_from_token_rows(rows)


def make_engine(rows=None):
    if rows is None:
        rows = [['.']]
    game_state = GameState(make_board(rows))
    return GameEngine(game_state, RuleEngine(), RealTimeArbiter())


def make_controller(rows=None, cell_size=None):
    engine = make_engine(rows)
    return Controller(engine, cell_size=cell_size), engine


def cell(row, col):
    return Position(row, col)


def pixel_for(row, col, cell_size=None):
    size = constants.CELL_SIZE if cell_size is None else cell_size
    return col * size + size // 2, row * size + size // 2


@pytest.fixture
def empty_8x8():
    return make_board([['.'] * 8 for _ in range(8)])
