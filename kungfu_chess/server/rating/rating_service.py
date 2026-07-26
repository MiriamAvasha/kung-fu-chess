from typing import Dict, Optional, Tuple

from server.auth.user_repository import UserRepository
from server.rating.elo import update_ratings


class RatingService:
    """Applies ELO updates through the user repository."""

    def __init__(self, repository: UserRepository):
        self._repository = repository

    def apply_match_result(
        self,
        winner_username: str,
        loser_username: str,
    ) -> Dict[str, int]:
        winner = self._repository.get_by_username(winner_username)
        loser = self._repository.get_by_username(loser_username)
        if winner is None or loser is None:
            raise ValueError('both players must exist before rating update')

        new_winner, new_loser = update_ratings(
            winner.rating,
            loser.rating,
            score_a=1.0,
        )
        self._repository.update_rating(winner.username, new_winner)
        self._repository.update_rating(loser.username, new_loser)
        return {
            winner.username: new_winner,
            loser.username: new_loser,
        }

    def ratings_for(
        self,
        username_a: str,
        username_b: str,
    ) -> Tuple[Optional[int], Optional[int]]:
        return self._repository.get_ratings(username_a, username_b)
