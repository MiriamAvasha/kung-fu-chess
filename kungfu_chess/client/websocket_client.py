import asyncio
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from client.home_screen import (
    prompt_credentials,
    prompt_home_action,
    prompt_room_dialog,
)
from client.terminal_ui import (
    _ui_lock,
    display_message,
    display_message_async,
    get_current_role,
    get_current_room_id,
    move_prompt,
    spectator_prompt,
)
from shared.activity_log import log_activity, setup_activity_logger
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
from shared.messages.types import ServerMessageType
from shared.protocol import decode_message, encode_message


URI = 'ws://localhost:8765'

# Logs go to logs/client.log only — keep the terminal for the game UI.
_logger = setup_activity_logger('kungfu.client', 'client.log', console=False)

MATCH_SUCCESS_TYPES = frozenset({
    ServerMessageType.MATCH_FOUND,
    ServerMessageType.INITIAL_STATE,
})

MATCH_FAILURE_TYPES = frozenset({
    ServerMessageType.NO_MATCH,
    ServerMessageType.ERROR,
})

ROOM_FAILURE_TYPES = frozenset({
    ServerMessageType.ERROR,
})


async def send_commands(websocket, spectator: bool = False):
    loop = asyncio.get_running_loop()
    prompt = spectator_prompt() if spectator else move_prompt()
    while True:
        async with _ui_lock:
            command = await loop.run_in_executor(None, input, prompt)
        command = command.strip()
        if command.lower() == '/quit':
            return
        if spectator:
            async with _ui_lock:
                print('Viewers cannot send moves.')
                print(prompt, end='', flush=True)
            continue
        if command:
            payload = encode_message(MoveRequest(command).to_dict())
            log_activity(_logger, 'OUT', payload)
            await websocket.send(payload)


async def receive_messages(websocket, reprompt: Optional[str] = None):
    async for raw_message in websocket:
        log_activity(_logger, 'IN', raw_message)
        await display_message_async(raw_message, reprompt=reprompt)


async def login(websocket, username: str, password: str) -> bool:
    payload = encode_message(JoinRequest(username, password).to_dict())
    log_activity(_logger, 'OUT', payload)
    await websocket.send(payload)
    raw_message = await websocket.recv()
    log_activity(_logger, 'IN', raw_message)
    display_message(raw_message)

    try:
        message = decode_message(raw_message)
    except (TypeError, ValueError):
        return False
    return message.get('type') == ServerMessageType.JOIN_ACCEPTED


async def wait_for_match(websocket) -> bool:
    payload = encode_message(PlayRequest().to_dict())
    log_activity(_logger, 'OUT', payload)
    await websocket.send(payload)
    while True:
        raw_message = await websocket.recv()
        log_activity(_logger, 'IN', raw_message)
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


async def wait_for_room(websocket, action: str, room_id: str = None) -> bool:
    if action == 'create':
        payload = encode_message(CreateRoomRequest().to_dict())
    else:
        payload = encode_message(JoinRoomRequest(room_id).to_dict())
    log_activity(_logger, 'OUT', payload)
    await websocket.send(payload)

    while True:
        raw_message = await websocket.recv()
        log_activity(_logger, 'IN', raw_message)
        display_message(raw_message)
        try:
            message = decode_message(raw_message)
        except (TypeError, ValueError):
            return False

        message_type = message.get('type')
        if message_type in ROOM_FAILURE_TYPES:
            return False
        if message_type == ServerMessageType.ROOM_CREATED:
            print('Share this room id: {}'.format(message.get('room_id')))
            print('Waiting for an opponent to join...')
            return True
        if message_type == ServerMessageType.ROOM_JOINED:
            role = message.get('role')
            if role == 'viewer' or message.get('game_started'):
                return True
            if role == 'b' and not message.get('game_started'):
                continue
            if role == 'w':
                continue
            return True
        if message_type in (
            ServerMessageType.INITIAL_STATE,
            ServerMessageType.GAME_STATE,
        ):
            return True


async def run_game_loop(websocket, spectator: bool = False):
    reprompt = spectator_prompt() if spectator else move_prompt()
    receiver = asyncio.create_task(
        receive_messages(websocket, reprompt=reprompt),
    )
    sender = asyncio.create_task(send_commands(websocket, spectator=spectator))
    done, pending = await asyncio.wait(
        {receiver, sender},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        task.result()


async def main(uri: str = URI):
    username, password = prompt_credentials()
    try:
        async with websockets.connect(uri) as websocket:
            print(f'Connected to {uri}')
            if not await login(websocket, username, password):
                print('Could not log in.')
                return

            loop = asyncio.get_running_loop()
            action = await loop.run_in_executor(None, prompt_home_action)
            if action == 'quit':
                return

            if action == 'play':
                matched = await wait_for_match(websocket)
                if not matched:
                    print('Could not start a match.')
                    return
                await run_game_loop(websocket, spectator=False)
                return

            room_action, room_id = await loop.run_in_executor(
                None,
                prompt_room_dialog,
            )
            if room_action == 'cancel':
                return

            ok = await wait_for_room(websocket, room_action, room_id)
            if not ok:
                print('Could not enter room.')
                return

            if get_current_room_id():
                print('In room {}'.format(get_current_room_id()))

            spectator = get_current_role() == 'viewer'
            await run_game_loop(websocket, spectator=spectator)
    except ConnectionClosed:
        print('Connection to server closed.')
    except OSError as error:
        print(f'Could not connect to {uri}: {error}')
