import sqlite3
from typing import Optional, Tuple

from server.auth.user import DEFAULT_RATING, UserAccount


class UserRepository:
    """SQLite persistence for user credentials and ratings."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self):
        self._connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                rating INTEGER NOT NULL
            )
            '''
        )
        self._connection.commit()

    def get_by_username(self, username: str) -> Optional[UserAccount]:
        row = self._connection.execute(
            'SELECT username, rating FROM users WHERE username = ?',
            (username,),
        ).fetchone()
        if row is None:
            return None
        return UserAccount(row['username'], int(row['rating']))

    def get_password_hash(self, username: str) -> Optional[str]:
        row = self._connection.execute(
            'SELECT password_hash FROM users WHERE username = ?',
            (username,),
        ).fetchone()
        if row is None:
            return None
        return row['password_hash']

    def create_user(
        self,
        username: str,
        password_hash: str,
        rating: int = DEFAULT_RATING,
    ) -> UserAccount:
        self._connection.execute(
            '''
            INSERT INTO users (username, password_hash, rating)
            VALUES (?, ?, ?)
            ''',
            (username, password_hash, rating),
        )
        self._connection.commit()
        return UserAccount(username, rating)

    def update_rating(self, username: str, rating: int) -> None:
        self._connection.execute(
            'UPDATE users SET rating = ? WHERE username = ?',
            (rating, username),
        )
        self._connection.commit()

    def get_ratings(
        self,
        username_a: str,
        username_b: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        account_a = self.get_by_username(username_a)
        account_b = self.get_by_username(username_b)
        rating_a = None if account_a is None else account_a.rating
        rating_b = None if account_b is None else account_b.rating
        return rating_a, rating_b
