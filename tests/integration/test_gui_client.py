import asyncio
import os


os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import websockets


from client.gui.app import GuiClientApp, Screen
from shared.messages.client_messages import (
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
)
from shared.protocol import encode_message
from tests.integration.test_websocket_game import (
    build_test_server,
    receive_json,
    wait_until,
)


async def wait_for(predicate, timeout=2):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() >= deadline:
            raise asyncio.TimeoutError()
        await asyncio.sleep(0.01)


async def graphical_room_scenario():
    game_server = build_test_server()
    app = None
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        app = GuiClientApp('ws://127.0.0.1:{}'.format(port))
        try:
            await app._connect_and_login('GuiAlice', 'pass1234')
            assert app.screen_name == Screen.HOME
            assert app.username == 'GuiAlice'

            app.display_surface = pygame.display.set_mode(
                (800, 600),
                pygame.RESIZABLE,
            )
            app._update_viewport()
            logical_position = (600, 380)
            display_position = (
                app.viewport_rect.left
                + int(logical_position[0] * app.viewport_scale),
                app.viewport_rect.top
                + int(logical_position[1] * app.viewport_scale),
            )
            mapped_position = app._display_to_logical(display_position)
            assert abs(mapped_position[0] - logical_position[0]) <= 1
            assert abs(mapped_position[1] - logical_position[1]) <= 1
            translated_event = app._event_to_logical(
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    {'pos': display_position, 'button': 1},
                )
            )
            assert abs(translated_event.pos[0] - logical_position[0]) <= 1
            assert abs(translated_event.pos[1] - logical_position[1]) <= 1
            app._draw()
            app._present()
            assert 'logout' in app.hitboxes

            app._create_room()
            await wait_for(lambda: app.screen_name == Screen.ROOM)
            assert app.room_id
            assert app.role == 'w'

            async with websockets.connect(app.uri) as opponent:
                await opponent.send(
                    encode_message(
                        JoinRequest('GuiBob', 'pass1234').to_dict(),
                    )
                )
                assert (await receive_json(opponent))['type'] == 'join_accepted'
                await opponent.send(
                    encode_message(
                        JoinRoomRequest(app.room_id).to_dict(),
                    )
                )

                await wait_for(lambda: app.screen_name == Screen.GAME)
                assert app.board.state is not None
                assert len(app.players) == 2
                app._draw()
                assert 'logout' in app.hitboxes

                board_rect = pygame.Rect(0, 0, 800, 800)
                app.board.handle_click((450, 650), board_rect)
                command, _ = app.board.handle_click((450, 650), board_rect)
                assert command == 'wPe2e2'

                await app._send_message(MoveRequest(command).to_dict())
                await wait_for(
                    lambda: bool(
                        app.board.state
                        and app.board.state.get('active_jumps')
                    )
                )
                app._draw()
                opponent_update = await wait_until(opponent, 'game_state')
                assert opponent_update['state']['active_jumps'][0]['at'] == [6, 4]

            await app._disconnect_to_login()
            assert app.screen_name == Screen.LOGIN
            assert app.connection is None
            assert app.username == ''
        finally:
            if app is not None:
                await app._shutdown()
            game_server.close()


def test_graphical_client_connects_to_real_room_server():
    asyncio.run(graphical_room_scenario())
