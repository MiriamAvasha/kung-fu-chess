"""Authentication and user persistence."""

from server.auth.auth_service import AuthError, AuthService
from server.auth.user import DEFAULT_RATING, UserAccount
from server.auth.user_repository import UserRepository

__all__ = [
    'AuthError',
    'AuthService',
    'DEFAULT_RATING',
    'UserAccount',
    'UserRepository',
]
