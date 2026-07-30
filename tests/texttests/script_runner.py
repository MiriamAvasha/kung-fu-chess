import sys

from engine.game_engine import GameEngine
from input.controller import Controller
from board_io.board_parser import BoardParser
from board_io.board_printer import BoardPrinter
from texttests.script_parser import ScriptParser


class ScriptRunner:
    def __init__(self, engine: GameEngine, controller: Controller, printer: BoardPrinter):
        self.engine = engine
        self.controller = controller
        self.printer = printer
        self.parser = ScriptParser()
        self._handlers = {
            'click': self._handle_click,
            'wait': self._handle_wait,
            'jump': self._handle_jump,
            'print_board': self._handle_print_board,
        }

    def _handle_click(self, command):
        self.controller.click(command[1], command[2])

    def _handle_wait(self, command):
        self.engine.wait(command[1])

    def _handle_jump(self, command):
        self.controller.jump(command[1], command[2])

    def _handle_print_board(self, command):
        self.printer.print_board(self.engine.game_state)

    def _execute(self, command):
        handler = self._handlers.get(command[0])
        if handler is not None:
            handler(command)

    def run(self, input_stream):
        parser = BoardParser()
        game_state = None

        for line in input_stream:
            cleaned_line = line.strip()
            if cleaned_line == "Commands:":
                break
            if not cleaned_line or cleaned_line.startswith("Board:"):
                continue
            game_state = parser.add_row(cleaned_line)

        self.engine.game_state = game_state
        self.controller.selected_cell = None

        for line in input_stream:
            cleaned_line = line.strip()
            if not cleaned_line:
                continue
            command = self.parser.parse(cleaned_line)
            if command is None:
                continue
            self._execute(command)
