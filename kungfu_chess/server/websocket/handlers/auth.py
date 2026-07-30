from typing import TYPE_CHECKING, Any

from server.auth import AuthError
from shared.messages.client_messages import JoinRequest
from shared.messages.server_messages import ErrorMessage, JoinAccepted

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class AuthHandlers:
    def __init__(self, server: 'GameServer'):
        self.server = server

    async def handle_join(
        self,
        websocket: Any,
        message: JoinRequest,
    ) -> None:
        if websocket in self.server.accounts:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'already_joined',
                    'already logged in on this connection',
                ),
            )
            return

        try:
            account = self.server.auth_service.login_or_register(
                message.username,
                message.password,
            )
        except AuthError as error:
            await self.server.send(
                websocket,
                ErrorMessage(error.code, error.message),
            )
            return

        self.server.accounts[websocket] = account
        if self.server.presence is not None:
            self.server.presence.set_online(account.username)
        await self.server.send(
            websocket,
            JoinAccepted(account.username, account.rating),
        )
        self.server.log(
            'SYS',
            'Player logged in: {} (rating {})'.format(
                account.username,
                account.rating,
            ),
        )
