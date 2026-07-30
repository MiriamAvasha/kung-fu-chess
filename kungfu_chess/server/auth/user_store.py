"""User store protocol shared by SQLite and PostgreSQL repositories."""

from typing import Optional, Protocol, Tuple

from server.auth.user import UserAccount


class UserStore(Protocol):
    def get_by_username(self, username: str) -> Optional[UserAccount]:
        ...

    def get_password_hash(self, username: str) -> Optional[str]:
        ...

    def create_user(
        self,
        username: str,
        password_hash: str,
        rating: int = ...,
    ) -> UserAccount:
        ...

    def update_rating(self, username: str, rating: int) -> None:
        ...

    def get_ratings(
        self,
        username_a: str,
        username_b: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        ...
