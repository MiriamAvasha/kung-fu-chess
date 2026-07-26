from shared.username import validate_username


def print_home_banner():
    print()
    print('==============================')
    print('       Kung Fu Chess')
    print('==============================')
    print('Terminal home — enter a username to join.')
    print('First player is White, second is Black.')
    print('Username: 1-20 letters, digits, or underscore.')
    print()


def prompt_username() -> str:
    print_home_banner()
    while True:
        raw = input('Username: ')
        ok, result = validate_username(raw)
        if ok:
            return result
        print('Invalid username: {}'.format(result))
