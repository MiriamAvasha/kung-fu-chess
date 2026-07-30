"""Player rating (ELO) services."""

from server.rating.elo import DEFAULT_K_FACTOR, expected_score, update_ratings
from server.rating.rating_service import RatingService

__all__ = [
    'DEFAULT_K_FACTOR',
    'RatingService',
    'expected_score',
    'update_ratings',
]
