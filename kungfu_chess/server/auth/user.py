DEFAULT_RATING = 1200


class UserAccount:
    """Public user identity used outside the persistence layer."""

    def __init__(self, username: str, rating: int = DEFAULT_RATING):
        self.username = username
        self.rating = rating
