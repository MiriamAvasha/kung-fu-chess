"""Persist finished games consumed from JetStream."""

from __future__ import annotations

import json
from typing import Any, Dict

import psycopg


class GameResultsRepository:
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
                    CREATE TABLE IF NOT EXISTS game_results (
                        id BIGSERIAL PRIMARY KEY,
                        room_id TEXT NOT NULL,
                        winner TEXT NOT NULL,
                        loser TEXT NOT NULL,
                        winner_rating INTEGER NOT NULL,
                        loser_rating INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (room_id, winner, loser, reason)
                    )
                    '''
                )
            connection.commit()

    def save_game_over(self, payload: Dict[str, Any]) -> bool:
        """Insert result. Returns False if duplicate."""
        with self._connect() as connection:
            with connection.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO game_results (
                        room_id, winner, loser,
                        winner_rating, loser_rating, reason, payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (room_id, winner, loser, reason) DO NOTHING
                    RETURNING id
                    ''',
                    (
                        payload.get('room_id', ''),
                        payload['winner'],
                        payload['loser'],
                        int(payload['ratings'][payload['winner']]),
                        int(payload['ratings'][payload['loser']]),
                        payload.get('reason', 'game_over'),
                        json.dumps(payload),
                    ),
                )
                row = cur.fetchone()
            connection.commit()
        return row is not None
