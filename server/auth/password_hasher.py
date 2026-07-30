import hashlib
import hmac
import os


ITERATIONS = 120000
SALT_BYTES = 16
HASH_NAME = 'sha256'


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode('utf-8'),
        salt,
        ITERATIONS,
    )
    return '{}${}${}'.format(
        ITERATIONS,
        salt.hex(),
        digest.hex(),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations_text, salt_hex, digest_hex = stored_hash.split('$', 2)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac(
        HASH_NAME,
        password.encode('utf-8'),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)
