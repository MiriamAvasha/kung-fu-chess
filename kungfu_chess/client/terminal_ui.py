from typing import Any, Dict

from shared.protocol import decode_message


COLOR_LABELS = {
    'w': 'White',
    'b': 'Black',
}


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


def display_message(raw_message: str):
    try:
        message = decode_message(raw_message)
    except (TypeError, ValueError):
        print(f'Server sent invalid JSON: {raw_message}')
        return

    message_type = message.get('type')
    if message_type == 'error':
        print(
            'Error [{}]: {}'.format(
                message.get('code'),
                message.get('message'),
            )
        )
        return

    if message_type == 'join_accepted':
        print(
            'Logged in as {} — rating {}'.format(
                message.get('username'),
                message.get('rating'),
            )
        )
        return

    if message_type == 'queue_status':
        print(
            'Searching for opponent (ELO +/- {}, timeout {}s)...'.format(
                message.get('elo_range'),
                message.get('timeout_seconds'),
            )
        )
        return

    if message_type == 'no_match':
        print('No player found.')
        print(message.get('message', 'no player found'))
        return

    if message_type == 'match_found':
        color = COLOR_LABELS.get(message.get('color'), message.get('color'))
        print(
            'Match found! You are {} ({}) — rating {}'.format(
                message.get('username'),
                color,
                message.get('rating'),
            )
        )
        players = message.get('players') or []
        if players:
            roster = ', '.join(
                '{}={} ({})'.format(
                    player.get('username'),
                    COLOR_LABELS.get(player.get('color'), player.get('color')),
                    player.get('rating'),
                )
                for player in players
            )
            print('Players: {}'.format(roster))
        return

    if message_type == 'disconnect_countdown':
        print(
            'Opponent disconnected countdown: {} — {}s remaining'.format(
                message.get('username'),
                message.get('seconds_remaining'),
            )
        )
        return

    if message_type == 'rating_update':
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
        return

    if message_type == 'move_result':
        status = 'accepted' if message.get('accepted') else 'rejected'
        print(
            '{}: {} ({})'.format(
                message.get('command'),
                status,
                message.get('reason'),
            )
        )
        return

    if message_type in ('initial_state', 'game_state'):
        if message_type == 'initial_state':
            print('Game starting!')
        print_board(message['state'])
        return

    print(f'Unknown server message: {message}')
