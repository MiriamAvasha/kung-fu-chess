"""CLI entry for texttest scripts (stdin Board/Commands harness)."""

import sys

from board_io.errors import BoardParseError
from engine.game_engine import GameEngine
from input.controller import Controller
from board_io.board_printer import BoardPrinter
from model.game_state import GameState
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import RuleEngine
from texttests.errors import ScriptParseError
from texttests.script_runner import ScriptRunner


def main():
    game_state = GameState()
    rule_engine = RuleEngine()
    arbiter = RealTimeArbiter()
    engine = GameEngine(game_state, rule_engine, arbiter)
    controller = Controller(engine)
    printer = BoardPrinter()
    runner = ScriptRunner(engine, controller, printer)
    try:
        runner.run(sys.stdin)
    except BoardParseError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
    except ScriptParseError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
