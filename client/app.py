from websockets.exceptions import ConnectionClosed

from client.game import run_game_loop
from client.home_screen import prompt_credentials
from client.menus import (
    login,
    prompt_session_choice,
    start_selected_session,
)
from client.network import DEFAULT_URI, GameConnection
from client.terminal_ui import get_current_role, get_current_room_id


async def main(uri: str = DEFAULT_URI) -> None:
    """Compose the client network, menu, and active-game layers."""
    username, password = prompt_credentials()

    try:
        async with await GameConnection.open(uri) as connection:
            print('Connected to {}'.format(uri))
            if not await login(connection, username, password):
                print('Could not log in.')
                return

            action, room_id = await prompt_session_choice()
            if action in ('quit', 'cancel'):
                return

            started = await start_selected_session(
                connection,
                action,
                room_id,
            )
            if not started:
                print('Could not start the selected session.')
                return

            if get_current_room_id():
                print('In room {}'.format(get_current_room_id()))

            await run_game_loop(
                connection,
                spectator=get_current_role() == 'viewer',
            )
    except ConnectionClosed:
        print('Connection to server closed.')
    except OSError as error:
        print('Could not connect to {}: {}'.format(uri, error))
