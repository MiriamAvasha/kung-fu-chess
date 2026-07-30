import json
from typing import Any, Dict

from engine.game_engine import GameEngine


def encode_message(message: Dict[str, Any]) -> str:
    return json.dumps(message, separators=(',', ':'))


def decode_message(raw_message: str) -> Dict[str, Any]:
    message = json.loads(raw_message)
    if not isinstance(message, dict):
        raise ValueError('message must be a JSON object')
    return message


def game_state_payload(engine: GameEngine) -> Dict[str, Any]:
    snapshot = engine.snapshot()
    motions = sorted(
        engine.arbiter.active_motions.values(),
        key=lambda motion: motion.order,
    )
    jumps = sorted(
        engine.arbiter.active_jumps.values(),
        key=lambda jump: (jump.row, jump.col),
    )
    return {
        'board_width': snapshot.board_width,
        'board_height': snapshot.board_height,
        'board': snapshot.token_grid,
        'game_over': snapshot.game_over,
        'server_time_ms': engine.arbiter.current_time,
        'active_motions': [
            {
                'piece': motion.piece_token,
                'from': [motion.from_row, motion.from_col],
                'to': [motion.to_row, motion.to_col],
                'started_at_ms': motion.start_time,
                'duration_ms': motion.duration,
            }
            for motion in motions
        ],
        'active_jumps': [
            {
                'piece': jump.piece_token,
                'at': [jump.row, jump.col],
                'started_at_ms': jump.start_time,
                'duration_ms': jump.duration,
            }
            for jump in jumps
        ],
    }


def state_message(message_type: str, engine: GameEngine) -> Dict[str, Any]:
    return {
        'type': message_type,
        'state': game_state_payload(engine),
    }


def error_message(code: str, message: str) -> Dict[str, Any]:
    from shared.messages.types import ServerMessageType

    return {
        'type': ServerMessageType.ERROR,
        'code': code,
        'message': message,
    }
