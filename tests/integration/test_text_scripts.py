"""Integration: TextTestRunner path — BoardParser + Controller + GameEngine + BoardPrinter.

Does not touch renderer / demo. Uses the public script harness only.
"""
from pathlib import Path

import pytest

from board_io.board_printer import BoardPrinter
from engine.game_engine import GameEngine
from input.controller import Controller
from model.game_state import GameState
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import RuleEngine
from texttests.script_runner import ScriptRunner

SCRIPTS_DIR = Path(__file__).resolve().parent / 'scripts'


def _run_script(path: Path) -> str:
    engine = GameEngine(GameState(), RuleEngine(), RealTimeArbiter())
    runner = ScriptRunner(engine, Controller(engine), BoardPrinter())
    with path.open(encoding='utf-8') as handle:
        runner.run(handle)
    return engine


@pytest.mark.parametrize('script_name', [
    '01_board_parsing',
    '02_click_to_move',
    '03_rook_moves',
    '04_invalid_moves',
    '05_capture',
    '06_game_over',
])
def test_text_script(script_name, capsys):
    script = SCRIPTS_DIR / f'{script_name}.kfc'
    expected = (SCRIPTS_DIR / f'{script_name}.expected').read_text(encoding='utf-8').strip()
    engine = _run_script(script)
    printed = capsys.readouterr().out.strip()
    assert printed == expected

    if script_name == '06_game_over':
        assert engine.game_state.game_over is True
