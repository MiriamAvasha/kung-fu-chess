import asyncio
from typing import Optional, Tuple

from client.home_screen import prompt_home_action, prompt_room_dialog
from client.network.connection import GameConnection
from client.terminal_ui import display_message
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    PlayRequest,
)
from shared.messages.types import ServerMessageType
from shared.protocol import decode_message


MATCH_SUCCESS_TYPES = frozenset({
    ServerMessageType.MATCH_FOUND,
    ServerMessageType.INITIAL_STATE,
})

MATCH_FAILURE_TYPES = frozenset({
    ServerMessageType.NO_MATCH,
    ServerMessageType.ERROR,
})

ROOM_STATE_TYPES = frozenset({
    ServerMessageType.ROOM_CREATED,
    ServerMessageType.ROOM_JOINED,
    ServerMessageType.INITIAL_STATE,
    ServerMessageType.GAME_STATE,
})


async def login(
    connection: GameConnection,
    username: str,
    password: str,
) -> bool:
    await connection.send_message(
        JoinRequest(username, password).to_dict(),
    )
    raw_message = await connection.receive_raw()
    display_message(raw_message)

    try:
        message = decode_message(raw_message)
    except (TypeError, ValueError):
        return False
    return message.get('type') == ServerMessageType.JOIN_ACCEPTED


async def wait_for_match(connection: GameConnection) -> bool:
    await connection.send_message(PlayRequest().to_dict())
    while True:
        raw_message = await connection.receive_raw()
        display_message(raw_message)
        try:
            message = decode_message(raw_message)
        except (TypeError, ValueError):
            return False

        message_type = message.get('type')
        if message_type in MATCH_SUCCESS_TYPES:
            return True
        if message_type in MATCH_FAILURE_TYPES:
            return False


async def wait_for_room(
    connection: GameConnection,
    action: str,
    room_id: Optional[str] = None,
) -> bool:
    if action == 'create':
        request = CreateRoomRequest()
    else:
        request = JoinRoomRequest(room_id or '')
    await connection.send_message(request.to_dict())

    while True:
        raw_message = await connection.receive_raw()
        display_message(raw_message)
        try:
            message = decode_message(raw_message)
        except (TypeError, ValueError):
            return False

        message_type = message.get('type')
        if message_type == ServerMessageType.ERROR:
            return False
        if message_type == ServerMessageType.ROOM_CREATED:
            print('Share this room id: {}'.format(message.get('room_id')))
            print('Waiting for an opponent to join...')
            return True
        if message_type in ROOM_STATE_TYPES:
            return True


async def prompt_session_choice() -> Tuple[str, Optional[str]]:
    """Run blocking home/room prompts outside the asyncio event loop."""
    loop = asyncio.get_running_loop()
    action = await loop.run_in_executor(None, prompt_home_action)
    if action != 'room':
        return action, None
    return await loop.run_in_executor(None, prompt_room_dialog)


async def start_selected_session(
    connection: GameConnection,
    action: str,
    room_id: Optional[str] = None,
) -> bool:
    if action == 'play':
        return await wait_for_match(connection)
    if action in ('create', 'join'):
        return await wait_for_room(connection, action, room_id)
    return False
