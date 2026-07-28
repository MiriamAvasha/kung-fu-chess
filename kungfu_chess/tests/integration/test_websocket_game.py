import asyncio
import contextlib
import json
import logging
import sqlite3

import websockets

from constants import PieceColor
from server.auth import AuthService, UserRepository
from server.matchmaking import Matchmaker
from server.rating import RatingService
from server.websocket_server import GameServer
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
from shared.protocol import encode_message


def silent_logger():
    logger = logging.getLogger('kungfu.test.server')
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


async def receive_json(websocket):
    raw_message = await asyncio.wait_for(websocket.recv(), timeout=2)
    return json.loads(raw_message)


async def login_as(websocket, username, password='pass1234'):
    await websocket.send(
        encode_message(JoinRequest(username, password).to_dict())
    )
    return await receive_json(websocket)


async def play(websocket):
    await websocket.send(encode_message(PlayRequest().to_dict()))


def build_test_server(auto_resign_seconds=20, timeout_seconds=60):
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    repository = UserRepository(connection)
    return GameServer(
        auth_service=AuthService(repository),
        rating_service=RatingService(repository),
        matchmaker=Matchmaker(
            elo_range=100,
            timeout_seconds=timeout_seconds,
        ),
        auto_resign_seconds=auto_resign_seconds,
        logger=silent_logger(),
    )


async def wait_until(websocket, message_type, timeout=2):
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError(message_type)
        message = await asyncio.wait_for(websocket.recv(), timeout=remaining)
        decoded = json.loads(message)
        if decoded.get('type') == message_type:
            return decoded


async def websocket_game_scenario():
    game_server = build_test_server()
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        uri = f'ws://127.0.0.1:{port}'

        async with websockets.connect(uri) as first_client:
            first_login = await login_as(first_client, 'Alice')
            assert first_login['type'] == 'join_accepted'
            assert first_login['rating'] == 1200

            await play(first_client)
            queue_status = await receive_json(first_client)
            assert queue_status['type'] == 'queue_status'

            async with websockets.connect(uri) as second_client:
                second_login = await login_as(second_client, 'Bob')
                assert second_login['type'] == 'join_accepted'

                await play(second_client)
                first_match = await wait_until(first_client, 'match_found')
                second_match = await wait_until(second_client, 'match_found')
                assert first_match['color'] == PieceColor.WHITE.value
                assert second_match['color'] == PieceColor.BLACK.value
                assert first_match.get('room_id')
                assert first_match['room_id'] == second_match['room_id']

                first_initial = await wait_until(first_client, 'initial_state')
                second_initial = await wait_until(second_client, 'initial_state')
                assert first_initial == second_initial

                await first_client.send(
                    encode_message(MoveRequest('WPe2e4').to_dict())
                )
                move_result = await receive_json(first_client)
                first_update = await receive_json(first_client)
                second_update = await receive_json(second_client)

                assert move_result['accepted'] is True
                assert first_update == second_update
                assert first_update['type'] == 'game_state'

                room = game_server.rooms.get(first_match['room_id'])
                room.session.advance(10000)
                await game_server.broadcast_game_state(room)
                first_arrival = await receive_json(first_client)
                second_arrival = await receive_json(second_client)
                assert first_arrival['state']['board'][4][4] == 'wP'
                assert second_arrival['state']['active_motions'] == []


async def websocket_no_match_and_auto_resign():
    game_server = build_test_server(
        auto_resign_seconds=1,
        timeout_seconds=1,
    )
    ticker = asyncio.create_task(game_server.run_ticker())
    try:
        async with websockets.serve(
            game_server.handle_client,
            '127.0.0.1',
            0,
        ) as running_server:
            port = running_server.sockets[0].getsockname()[1]
            uri = f'ws://127.0.0.1:{port}'

            async with websockets.connect(uri) as lonely:
                await login_as(lonely, 'Solo')
                await play(lonely)
                assert (await receive_json(lonely))['type'] == 'queue_status'
                no_match = await wait_until(lonely, 'no_match', timeout=3)
                assert no_match['message'] == 'no player found'

            async with websockets.connect(uri) as first_client:
                await login_as(first_client, 'Alice')
                await play(first_client)
                await receive_json(first_client)  # queue_status

                async with websockets.connect(uri) as second_client:
                    await login_as(second_client, 'Bob')
                    await play(second_client)
                    await wait_until(first_client, 'match_found')
                    await wait_until(second_client, 'match_found')
                    await wait_until(first_client, 'initial_state')
                    await wait_until(second_client, 'initial_state')

                countdown = await wait_until(
                    first_client,
                    'disconnect_countdown',
                    timeout=3,
                )
                assert countdown['username'] == 'Bob'
                rating_update = await wait_until(
                    first_client,
                    'rating_update',
                    timeout=3,
                )
                assert rating_update['reason'] == 'auto_resign'
                assert rating_update['winner'] == 'Alice'
                assert rating_update['loser'] == 'Bob'
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker


async def websocket_room_create_join_and_viewer():
    game_server = build_test_server()
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        uri = f'ws://127.0.0.1:{port}'

        async with websockets.connect(uri) as white_client:
            await login_as(white_client, 'Alice')
            await white_client.send(
                encode_message(CreateRoomRequest().to_dict())
            )
            created = await receive_json(white_client)
            assert created['type'] == 'room_created'
            assert created['role'] == PieceColor.WHITE.value
            room_id = created['room_id']

            async with websockets.connect(uri) as black_client:
                await login_as(black_client, 'Bob')
                await black_client.send(
                    encode_message(JoinRoomRequest(room_id).to_dict())
                )
                white_joined = await wait_until(white_client, 'room_joined')
                black_joined = await wait_until(black_client, 'room_joined')
                assert white_joined['role'] == PieceColor.WHITE.value
                assert black_joined['role'] == PieceColor.BLACK.value
                assert white_joined['game_started'] is True

                white_initial = await wait_until(white_client, 'initial_state')
                black_initial = await wait_until(black_client, 'initial_state')
                assert white_initial == black_initial

                async with websockets.connect(uri) as viewer_client:
                    await login_as(viewer_client, 'Carol')
                    await viewer_client.send(
                        encode_message(JoinRoomRequest(room_id).to_dict())
                    )
                    viewer_joined = await wait_until(
                        viewer_client,
                        'room_joined',
                    )
                    assert viewer_joined['role'] == 'viewer'
                    await wait_until(viewer_client, 'game_state')

                    await viewer_client.send(
                        encode_message(MoveRequest('WPe2e4').to_dict())
                    )
                    error = await receive_json(viewer_client)
                    assert error['type'] == 'error'
                    assert error['code'] == 'viewer_cannot_move'

                # Casual room: no rating_update after forced resign.
                room = game_server.rooms.get(room_id)
                room.session.resign(PieceColor.BLACK.value)
                await game_server._maybe_apply_ratings(room)
                assert room.ratings_applied is True
                assert room.rated is False


async def websocket_two_rooms_are_isolated():
    game_server = build_test_server()
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        uri = f'ws://127.0.0.1:{port}'

        async with websockets.connect(uri) as a1:
            await login_as(a1, 'A1')
            await a1.send(encode_message(CreateRoomRequest().to_dict()))
            room_a = (await receive_json(a1))['room_id']

            async with websockets.connect(uri) as b1:
                await login_as(b1, 'B1')
                await b1.send(encode_message(CreateRoomRequest().to_dict()))
                room_b = (await receive_json(b1))['room_id']
                assert room_a != room_b

                async with websockets.connect(uri) as a2:
                    await login_as(a2, 'A2')
                    await a2.send(
                        encode_message(JoinRoomRequest(room_a).to_dict())
                    )
                    await wait_until(a1, 'initial_state')
                    await wait_until(a2, 'initial_state')

                    async with websockets.connect(uri) as b2:
                        await login_as(b2, 'B2')
                        await b2.send(
                            encode_message(JoinRoomRequest(room_b).to_dict())
                        )
                        await wait_until(b1, 'initial_state')
                        await wait_until(b2, 'initial_state')

                        await a1.send(
                            encode_message(MoveRequest('WPe2e4').to_dict())
                        )
                        await receive_json(a1)  # move_result
                        update_a = await receive_json(a1)
                        update_a2 = await receive_json(a2)
                        assert update_a['type'] == 'game_state'
                        assert update_a2 == update_a

                        with contextlib.suppress(asyncio.TimeoutError):
                            unexpected = await asyncio.wait_for(
                                b1.recv(),
                                timeout=0.2,
                            )
                            raise AssertionError(
                                'room B received room A traffic: {}'.format(
                                    unexpected,
                                )
                            )


def test_two_clients_match_and_share_state():
    asyncio.run(websocket_game_scenario())


def test_no_match_timeout_and_auto_resign():
    asyncio.run(websocket_no_match_and_auto_resign())


def test_room_create_join_viewer_no_elo():
    asyncio.run(websocket_room_create_join_and_viewer())


def test_two_rooms_isolated():
    asyncio.run(websocket_two_rooms_are_isolated())
