import asyncio
import json

import websockets

from server.websocket_server import GameServer
from shared.messages import JoinRequest, MoveRequest
from shared.protocol import encode_message


async def receive_json(websocket):
    raw_message = await asyncio.wait_for(websocket.recv(), timeout=2)
    return json.loads(raw_message)


async def join_as(websocket, username):
    await websocket.send(
        encode_message(JoinRequest(username).to_dict())
    )
    return await receive_json(websocket)


async def websocket_game_scenario():
    game_server = GameServer()
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        uri = f'ws://127.0.0.1:{port}'

        async with websockets.connect(uri) as first_client:
            first_join = await join_as(first_client, 'Alice')
            assert first_join['type'] == 'join_accepted'
            assert first_join['color'] == 'w'

            async with websockets.connect(uri) as second_client:
                second_join = await join_as(second_client, 'Bob')
                assert second_join['type'] == 'join_accepted'
                assert second_join['color'] == 'b'

                first_initial = await receive_json(first_client)
                second_initial = await receive_json(second_client)
                assert first_initial == second_initial
                assert first_initial['type'] == 'initial_state'

                await first_client.send(
                    encode_message(MoveRequest('WPe2e4').to_dict())
                )
                move_result = await receive_json(first_client)
                first_update = await receive_json(first_client)
                second_update = await receive_json(second_client)

                assert move_result['type'] == 'move_result'
                assert move_result['accepted'] is True
                assert first_update == second_update
                assert first_update['type'] == 'game_state'
                assert first_update['state']['active_motions']

                game_server.session.advance(10000)
                await game_server.broadcast_game_state()
                first_arrival = await receive_json(first_client)
                second_arrival = await receive_json(second_client)

                assert first_arrival == second_arrival
                assert first_arrival['state']['board'][4][4] == 'wP'
                assert first_arrival['state']['active_motions'] == []


async def websocket_rejects_third_player_and_wrong_color():
    game_server = GameServer()
    async with websockets.serve(
        game_server.handle_client,
        '127.0.0.1',
        0,
    ) as running_server:
        port = running_server.sockets[0].getsockname()[1]
        uri = f'ws://127.0.0.1:{port}'

        async with websockets.connect(uri) as first_client:
            await join_as(first_client, 'Alice')
            async with websockets.connect(uri) as second_client:
                await join_as(second_client, 'Bob')
                await receive_json(first_client)
                await receive_json(second_client)

                async with websockets.connect(uri) as third_client:
                    third_join = await join_as(third_client, 'Carol')
                    assert third_join['type'] == 'error'
                    assert third_join['code'] == 'room_full'

                await second_client.send(
                    encode_message(MoveRequest('WPe2e4').to_dict())
                )
                wrong_color = await receive_json(second_client)
                assert wrong_color['type'] == 'move_result'
                assert wrong_color['accepted'] is False
                assert wrong_color['reason'] == 'wrong_color'


def test_two_clients_receive_the_same_authoritative_state():
    asyncio.run(websocket_game_scenario())


def test_third_player_rejected_and_color_enforced():
    asyncio.run(websocket_rejects_third_player_and_wrong_color())
