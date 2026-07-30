from typing import Any, Dict, Optional, Tuple

from constants import PieceColor, PieceKind, opponent_color
from engine.game_engine import GameEngine
from server.move_parser import MoveCommandError, parse_move_command
from shared.messages.types import ServerMessageType
from shared.protocol import error_message, game_state_payload


class GameSession:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self._resign_winner_color: Optional[str] = None

    def initial_message(self) -> Dict[str, Any]:
        return {
            'type': ServerMessageType.INITIAL_STATE,
            'state': game_state_payload(self.engine),
        }

    def game_state_message(self) -> Dict[str, Any]:
        return {
            'type': ServerMessageType.GAME_STATE,
            'state': game_state_payload(self.engine),
        }

    @property
    def is_game_over(self) -> bool:
        return self.engine.game_state.game_over

    def resign(self, loser_color: str) -> str:
        """End the game by resignation; returns winner color."""
        winner_color = opponent_color(loser_color)
        self.engine.game_state.game_over = True
        self._resign_winner_color = winner_color
        return winner_color

    def winner_color(self) -> Optional[str]:
        if not self.is_game_over:
            return None
        if self._resign_winner_color is not None:
            return self._resign_winner_color
        has_white_king = False
        has_black_king = False
        for piece in self.engine.game_state.board.all_pieces():
            if piece.kind != PieceKind.KING.value:
                continue
            if piece.color == PieceColor.WHITE.value:
                has_white_king = True
            elif piece.color == PieceColor.BLACK.value:
                has_black_king = True
        if has_white_king and not has_black_king:
            return PieceColor.WHITE.value
        if has_black_king and not has_white_king:
            return PieceColor.BLACK.value
        return None




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
                'type': ServerMessageType.MOVE_RESULT,
                'command': command.raw,
                'accepted': False,
                'reason': 'wrong_color',
                'state': game_state_payload(self.engine),
            }

        piece = self.engine.game_state.board.piece_at(command.source)
        if piece is not None and piece.token != command.token:
            return {
                'type': ServerMessageType.MOVE_RESULT,
                'command': command.raw,
                'accepted': False,
                'reason': 'piece_mismatch',
                'state': game_state_payload(self.engine),
            }

        if command.source == command.destination:
            result = self.engine.request_jump(command.source)
        else:
            result = self.engine.request_move(
                command.source,
                command.destination,
            )
        return {
            'type': ServerMessageType.MOVE_RESULT,
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
        jumps = tuple(
            (
                jump.piece_id,
                jump.row,
                jump.col,
                jump.start_time,
                jump.end_time,
            )
            for jump in sorted(
                self.engine.arbiter.active_jumps.values(),
                key=lambda active: (active.row, active.col),
            )
        )
        return board, snapshot.game_over, motions, jumps
