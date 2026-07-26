from typing import Tuple

from shared.password import validate_password
from shared.username import validate_username


def print_home_banner():
    print()
    print('==============================')
    print('       Kung Fu Chess')
    print('==============================')
    print('Terminal home — login or register.')
    print('Then press Play to find an opponent (ELO +/- 100).')
    print('Username: 1-20 letters, digits, or underscore.')
    print('Password: at least 4 characters.')
    print('New accounts start at rating 1200.')
    print()


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


def prompt_play() -> bool:
    print()
    print('[Play] Search for an opponent within ELO +/- 100')
    print('       Wait up to 60 seconds. Type /quit to exit.')
    while True:
        choice = input('Press Enter to Play (or /quit): ').strip()
        if choice.lower() == '/quit':
            return False
        if choice == '' or choice.lower() in ('play', 'p'):
            return True
        print('Type Enter/Play to search, or /quit to exit.')
