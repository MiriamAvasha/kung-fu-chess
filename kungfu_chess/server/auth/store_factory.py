"""Choose SQLite or PostgreSQL user persistence from environment."""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple

from server.auth.postgres_user_repository import PostgresUserRepository
from server.auth.user_repository import UserRepository
from server.auth.user_store import UserStore
from server.db import open_database
from server.infra.settings import DATABASE_URL


def persistence_backend() -> str:
    explicit = os.environ.get('KUNGFU_PERSISTENCE', '').strip().lower()
    if explicit in ('sqlite', 'postgres', 'postgresql'):
        if explicit == 'postgresql':
            return 'postgres'
        return explicit
    if DATABASE_URL.startswith('postgres'):
        return 'postgres'
    return 'sqlite'


def open_user_store(
    db_path=None,
) -> Tuple[UserStore, Optional[Any]]:
    """
    Returns (repository, sqlite_connection_or_None).

    Caller must keep the SQLite connection alive for the process lifetime.
    """
    backend = persistence_backend()
    if backend == 'postgres':
        if not DATABASE_URL:
            raise RuntimeError(
                'DATABASE_URL is required when KUNGFU_PERSISTENCE=postgres'
            )
        return PostgresUserRepository(DATABASE_URL), None

    connection = open_database(db_path)
    return UserRepository(connection), connection
