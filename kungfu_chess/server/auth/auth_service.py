from server.auth.password_hasher import hash_password, verify_password
from server.auth.user import UserAccount
from server.auth.user_repository import UserRepository
from shared.password import validate_password
from shared.username import validate_username


class AuthError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class AuthService:
    """Application service: credential validation against the user store."""

    def __init__(self, repository: UserRepository):
        self._repository = repository

    def login_or_register(self, username: str, password: str) -> UserAccount:
        ok_username, username_result = validate_username(username)
        if not ok_username:
            raise AuthError('invalid_username', username_result)

        ok_password, password_result = validate_password(password)
        if not ok_password:
            raise AuthError('invalid_password', password_result)

        existing = self._repository.get_by_username(username_result)
        if existing is None:
            password_hash = hash_password(password_result)
            return self._repository.create_user(
                username_result,
                password_hash,
            )

        stored_hash = self._repository.get_password_hash(username_result)
        if stored_hash is None or not verify_password(password_result, stored_hash):
            raise AuthError('invalid_credentials', 'incorrect password')

        return existing
