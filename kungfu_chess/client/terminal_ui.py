from typing import Any, Callable, Dict

from constants import color_display_name
from shared.messages.types import ServerMessageType
from shared.protocol import decode_message


MessageHandler = Callable[[Dict[str, Any]], None]


def print_board(state: Dict[str, Any]):
    board = state['board']
    height = state['board_height']
    width = state['board_width']
    print()
    for row_index, row in enumerate(board):
        rank = height - row_index
        print(f"{rank}  {' '.join(row)}")
    files = ' '.join(chr(ord('a') + index) for index in range(width))
    print(f'   {files}')

    motions = state.get('active_motions', [])
    if motions:
        moving = ', '.join(
            '{} moving'.format(motion['piece'])
            for motion in motions
        )
        print(f'Active: {moving}')
    if state.get('game_over'):
        print('GAME OVER')
    print()


def _show_error(message: Dict[str, Any]):
    print(
        'Error [{}]: {}'.format(
            message.get('code'),
            message.get('message'),
        )
    )


def _show_join_accepted(message: Dict[str, Any]):
    print(
        'Logged in as {} — rating {}'.format(
            message.get('username'),
            message.get('rating'),
        )
    )


def _show_queue_status(message: Dict[str, Any]):
    print(
        'Searching for opponent (ELO +/- {}, timeout {}s)...'.format(
            message.get('elo_range'),
            message.get('timeout_seconds'),
        )
    )


def _show_no_match(message: Dict[str, Any]):
    print('No player found.')
    print(message.get('message', 'no player found'))


def _show_match_found(message: Dict[str, Any]):
    color = color_display_name(message.get('color'))
    print(
        'Match found! You are {} ({}) — rating {}'.format(
            message.get('username'),
            color,
            message.get('rating'),
        )
    )
    players = message.get('players') or []
    if not players:
        return
    roster = ', '.join(
        '{}={} ({})'.format(
            player.get('username'),
            color_display_name(player.get('color')),
            player.get('rating'),
        )
        for player in players
    )
    print('Players: {}'.format(roster))


def _show_disconnect_countdown(message: Dict[str, Any]):
    print(
        'Opponent disconnected countdown: {} — {}s remaining'.format(
            message.get('username'),
            message.get('seconds_remaining'),
        )
    )


def _show_rating_update(message: Dict[str, Any]):
    ratings = message.get('ratings') or {}
    reason = message.get('reason') or 'game_over'
    print(
        'Match result ({}): {} beat {}'.format(
            reason,
            message.get('winner'),
            message.get('loser'),
        )
    )
    for username, rating in ratings.items():
        print('  {} -> rating {}'.format(username, rating))


def _show_move_result(message: Dict[str, Any]):
    status = 'accepted' if message.get('accepted') else 'rejected'
    print(
        '{}: {} ({})'.format(
            message.get('command'),
            status,
            message.get('reason'),
        )
    )


def _show_board_state(message: Dict[str, Any]):
    if message.get('type') == ServerMessageType.INITIAL_STATE:
        print('Game starting!')
    print_board(message['state'])


MESSAGE_HANDLERS: Dict[str, MessageHandler] = {
    ServerMessageType.ERROR: _show_error,
    ServerMessageType.JOIN_ACCEPTED: _show_join_accepted,
    ServerMessageType.QUEUE_STATUS: _show_queue_status,
    ServerMessageType.NO_MATCH: _show_no_match,
    ServerMessageType.MATCH_FOUND: _show_match_found,
    ServerMessageType.DISCONNECT_COUNTDOWN: _show_disconnect_countdown,
    ServerMessageType.RATING_UPDATE: _show_rating_update,
    ServerMessageType.MOVE_RESULT: _show_move_result,
    ServerMessageType.INITIAL_STATE: _show_board_state,
    ServerMessageType.GAME_STATE: _show_board_state,
}


def display_message(raw_message: str):
    try:
        message = decode_message(raw_message)
    except (TypeError, ValueError):
        print(f'Server sent invalid JSON: {raw_message}')
        return

    handler = MESSAGE_HANDLERS.get(message.get('type'))
    if handler is None:
        print(f'Unknown server message: {message}')
        return
    handler(message)
