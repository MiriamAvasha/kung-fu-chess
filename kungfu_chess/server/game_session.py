from typing import Any, Dict, Tuple

from engine.game_engine import GameEngine
from server.move_parser import MoveCommandError, parse_move_command
from shared.protocol import error_message, game_state_payload


class GameSession:
    def __init__(self, engine: GameEngine):
        self.engine = engine

    def initial_message(self) -> Dict[str, Any]:
        return {
            'type': 'initial_state',
            'state': game_state_payload(self.engine),
        }

    def game_state_message(self) -> Dict[str, Any]:
        return {
            'type': 'game_state',
            'state': game_state_payload(self.engine),
        }

    def handle_command(
        self,
        raw_command: str,
        player_color: str,
    ) -> Dict[str, Any]:
        try:
            command = parse_move_command(raw_command)
        except MoveCommandError as error:
            return error_message('invalid_command', str(error))

        if command.token[0] != player_color:
            return {
                'type': 'move_result',
                'command': command.raw,
                'accepted': False,
                'reason': 'wrong_color',
                'state': game_state_payload(self.engine),
            }

        piece = self.engine.game_state.board.piece_at(command.source)
        if piece is not None and piece.token != command.token:
            return {
                'type': 'move_result',
                'command': command.raw,
                'accepted': False,
                'reason': 'piece_mismatch',
                'state': game_state_payload(self.engine),
            }

        result = self.engine.request_move(
            command.source,
            command.destination,
        )
        return {
            'type': 'move_result',
            'command': command.raw,
            'accepted': result.is_accepted,
            'reason': result.reason,
            'state': game_state_payload(self.engine),
        }

    def advance(self, elapsed_ms: int) -> bool:
        before = self._state_fingerprint()
        self.engine.wait(elapsed_ms)
        return before != self._state_fingerprint()

    def _state_fingerprint(self) -> Tuple[Any, ...]:
        snapshot = self.engine.snapshot()
        board = tuple(tuple(row) for row in snapshot.token_grid)
        motions = tuple(
            (
                motion.piece_id,
                motion.from_row,
                motion.from_col,
                motion.to_row,
                motion.to_col,
                motion.arrival_time,
            )
            for motion in sorted(
                self.engine.arbiter.active_motions.values(),
                key=lambda active: active.order,
            )
        )
        return board, snapshot.game_over, motions
