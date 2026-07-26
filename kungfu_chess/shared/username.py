import re
from typing import Optional, Tuple


USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{1,20}$')


def normalize_username(raw: str) -> str:
    if not isinstance(raw, str):
        return ''
    return raw.strip()


def validate_username(raw: str) -> Tuple[bool, Optional[str]]:
    username = normalize_username(raw)
    if not username:
        return False, 'username must not be empty'
    if not USERNAME_PATTERN.fullmatch(username):
        return False, (
            'username must be 1-20 characters: letters, digits, underscore'
        )
    return True, username
