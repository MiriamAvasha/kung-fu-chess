from typing import TYPE_CHECKING

from constants import opponent_color
from server.auth import UserAccount
from server.rooms import Room
from shared.messages.server_messages import RatingUpdate

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class RatingCoordinator:
    """Apply ELO exactly once for rated rooms after game over."""

    def __init__(self, server: 'GameServer'):
        self.server = server

    async def maybe_apply(
        self,
        room: Room,
        reason: str = 'game_over',
    ) -> None:
        if room.ratings_applied or not room.session.is_game_over:
            return
        if not room.rated:
            room.ratings_applied = True
            return

        winner_color = room.session.winner_color()
        if winner_color is None:
            return

        winner = room.get_by_color(winner_color)
        loser = room.get_by_color(opponent_color(winner_color))
        if winner is None or loser is None:
            return

        ratings = self.server.rating_service.apply_match_result(
            winner.username,
            loser.username,
        )
        room.update_ratings(ratings)
        for connection, account in list(self.server.accounts.items()):
            if account.username in ratings:
                self.server.accounts[connection] = UserAccount(
                    account.username,
                    ratings[account.username],
                )

        room.ratings_applied = True
        await self.server.broadcast_room(
            room,
            RatingUpdate(
                winner=winner.username,
                loser=loser.username,
                ratings=ratings,
                reason=reason,
            ),
        )
