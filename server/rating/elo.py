import math
from typing import Tuple


DEFAULT_K_FACTOR = 32


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))


def update_ratings(
    rating_a: int,
    rating_b: int,
    score_a: float,
    k_factor: int = DEFAULT_K_FACTOR,
) -> Tuple[int, int]:
    """Return new (rating_a, rating_b) after a game.

    score_a is 1.0 for win, 0.5 for draw, 0.0 for loss.
    """
    expected_a = expected_score(rating_a, rating_b)
    expected_b = 1.0 - expected_a
    score_b = 1.0 - score_a
    new_a = int(round(rating_a + k_factor * (score_a - expected_a)))
    new_b = int(round(rating_b + k_factor * (score_b - expected_b)))
    return new_a, new_b
