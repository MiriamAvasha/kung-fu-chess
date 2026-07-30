"""PostgreSQL persistence for user credentials and ratings."""

from typing import Optional, Tuple

import psycopg

from server.auth.user import DEFAULT_RATING, UserAccount


class PostgresUserRepository:
    """Postgres-backed user store (Compose / production)."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._ensure_schema()

    def _connect(self):
        return psycopg.connect(self._database_url)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        rating INTEGER NOT NULL
                    )
                    '''
                )
                cur.execute(
                    '''
                    CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower
                    ON users (LOWER(username))
                    '''
                )
            connection.commit()

    def get_by_username(self, username: str) -> Optional[UserAccount]:
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    SELECT username, rating FROM users
                    WHERE LOWER(username) = LOWER(%s)
                    ''',
                    (username,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return UserAccount(row[0], int(row[1]))

    def get_password_hash(self, username: str) -> Optional[str]:
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    SELECT password_hash FROM users
                    WHERE LOWER(username) = LOWER(%s)
                    ''',
                    (username,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return row[0]

    def create_user(
        self,
        username: str,
        password_hash: str,
        rating: int = DEFAULT_RATING,
    ) -> UserAccount:
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO users (username, password_hash, rating)
                    VALUES (%s, %s, %s)
                    ''',
                    (username, password_hash, rating),
                )
            connection.commit()
        return UserAccount(username, rating)

    def update_rating(self, username: str, rating: int) -> None:
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE users SET rating = %s
                    WHERE LOWER(username) = LOWER(%s)
                    ''',
                    (rating, username),
                )
            connection.commit()

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
