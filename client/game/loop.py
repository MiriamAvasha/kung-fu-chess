import asyncio

from client.network.connection import GameConnection
from client.terminal_ui import (
    display_message_async,
    move_prompt,
    spectator_prompt,
)
from shared.messages.client_messages import MoveRequest


async def send_commands(
    connection: GameConnection,
    spectator: bool = False,
) -> None:
    """Read terminal commands and send legal client actions."""
    loop = asyncio.get_running_loop()
    prompt = spectator_prompt() if spectator else move_prompt()

    while True:
        command = await loop.run_in_executor(None, input, prompt)
        command = command.strip()
        if command.lower() == '/quit':
            return
        if spectator:
            print('Viewers cannot send moves.')
            continue
        if command:
            await connection.send_message(
                MoveRequest(command).to_dict(),
            )


async def receive_messages(
    connection: GameConnection,
    reprompt: str,
) -> None:
    """Render all server updates received during an active game."""
    async for raw_message in connection.incoming():
        await display_message_async(raw_message, reprompt=reprompt)


async def run_game_loop(
    connection: GameConnection,
    spectator: bool = False,
) -> None:
    """Run terminal input and board updates until either side finishes."""
    prompt = spectator_prompt() if spectator else move_prompt()
    receiver = asyncio.create_task(
        receive_messages(connection, reprompt=prompt),
    )
    sender = asyncio.create_task(
        send_commands(connection, spectator=spectator),
    )
    done, pending = await asyncio.wait(
        {receiver, sender},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        task.result()
