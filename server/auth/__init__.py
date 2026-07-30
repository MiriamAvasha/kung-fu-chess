"""Authentication and user persistence."""

from server.auth.auth_service import AuthError, AuthService
from server.auth.postgres_user_repository import PostgresUserRepository
from server.auth.store_factory import open_user_store, persistence_backend
from server.auth.user import DEFAULT_RATING, UserAccount
from server.auth.user_repository import UserRepository
from server.auth.user_store import UserStore

__all__ = [
    'AuthError',
    'AuthService',
    'DEFAULT_RATING',
    'PostgresUserRepository',
    'UserAccount',
    'UserRepository',
    'UserStore',
    'open_user_store',
    'persistence_backend',
]
