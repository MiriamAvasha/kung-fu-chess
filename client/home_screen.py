from typing import Optional, Tuple

from shared.password import validate_password
from shared.username import validate_username


def print_home_banner(room_id: Optional[str] = None):
    print()
    print('==============================')
    print('       Kung Fu Chess')
    if room_id:
        print('       Room: {}'.format(room_id))
    print('==============================')
    print('Terminal home — login or register.')
    print('Then choose Play (ELO matchmaking) or Room (create/join).')
    print('Username: 1-20 letters, digits, or underscore.')
    print('Password: at least 4 characters.')
    print('New accounts start at rating 1200.')
    print()


def print_room_header(room_id: str, role: Optional[str] = None):
    print()
    print('==============================')
    print('       Kung Fu Chess')
    print('       Room: {}'.format(room_id))
    if role:
        print('       Role: {}'.format(role))
    print('==============================')


def prompt_credentials() -> Tuple[str, str]:
    print_home_banner()
    while True:
        raw_username = input('Username: ')
        ok_username, username = validate_username(raw_username)
        if not ok_username:
            print('Invalid username: {}'.format(username))
            continue

        raw_password = input('Password: ')
        ok_password, password = validate_password(raw_password)
        if not ok_password:
            print('Invalid password: {}'.format(password))
            continue

        return username, password


def prompt_home_action() -> str:
    """Return 'play', 'room', or 'quit'."""
    print()
    print('[Play] Search for an opponent within ELO +/- 100')
    print('[Room] Create or join a casual room (no ELO)')
    print('Type /quit to exit.')
    while True:
        choice = input('Play / Room / Quit: ').strip().lower()
        if choice in ('/quit', 'quit', 'q'):
            return 'quit'
        if choice in ('', 'play', 'p'):
            return 'play'
        if choice in ('room', 'r'):
            return 'room'
        print('Type Play, Room, or Quit.')


def prompt_room_dialog() -> Tuple[str, Optional[str]]:
    """
    Room dialog: Create / Join / Cancel.

    Returns ('create', None), ('join', room_id), or ('cancel', None).
    Typing a room id directly is treated as Join.
    """
    print()
    print('--- Room ---')
    print('Create: make a new room (you are White)')
    print('Join:   enter a room id (2nd = Black, others = viewers)')
    print('Cancel: return to home')
    print('Tip: you can paste a room id here to join immediately.')
    while True:
        choice = input('Create / Join / Cancel (or room id): ').strip()
        lowered = choice.lower()
        if lowered in ('cancel', 'c', ''):
            return 'cancel', None
        if lowered in ('create', 'cr'):
            return 'create', None
        if lowered in ('join', 'j'):
            room_id = input('Room id: ').strip()
            if not room_id:
                print('Room id is required to join.')
                continue
            return 'join', room_id
        # Any other non-empty text is treated as a room id to join.
        return 'join', choice
