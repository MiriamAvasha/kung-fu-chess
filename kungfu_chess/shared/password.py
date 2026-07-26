from typing import Optional, Tuple


MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 64


def validate_password(raw: str) -> Tuple[bool, Optional[str]]:
    if not isinstance(raw, str):
        return False, 'password must be a string'
    if len(raw) < MIN_PASSWORD_LENGTH:
        return False, 'password must be at least {} characters'.format(
            MIN_PASSWORD_LENGTH
        )
    if len(raw) > MAX_PASSWORD_LENGTH:
        return False, 'password must be at most {} characters'.format(
            MAX_PASSWORD_LENGTH
        )
    return True, raw
