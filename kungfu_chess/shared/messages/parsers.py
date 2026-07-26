from typing import Any, Dict, Union

from shared.messages.client_messages import JoinRequest, MoveRequest
from shared.messages.errors import ProtocolError
from shared.messages.server_messages import (
    ErrorMessage,
    JoinAccepted,
    PlayerInfo,
)
from shared.protocol import decode_message


ClientMessage = Union[JoinRequest, MoveRequest]
ServerMessage = Union[JoinAccepted, ErrorMessage]


def parse_player_info(data: Any) -> PlayerInfo:
    if not isinstance(data, dict):
        raise ProtocolError('player must be an object')
    username = data.get('username')
    color = data.get('color')
    if not isinstance(username, str) or not isinstance(color, str):
        raise ProtocolError('player.username and player.color must be strings')
    return PlayerInfo(username, color)


def parse_join_request(data: Dict[str, Any]) -> JoinRequest:
    username = data.get('username')
    if not isinstance(username, str):
        raise ProtocolError('join.username must be a string')
    return JoinRequest(username)


def parse_move_request(data: Dict[str, Any]) -> MoveRequest:
    command = data.get('command')
    if not isinstance(command, str):
        raise ProtocolError('move.command must be a string')
    return MoveRequest(command)


def parse_join_accepted(data: Dict[str, Any]) -> JoinAccepted:
    username = data.get('username')
    color = data.get('color')
    players_raw = data.get('players')
    if not isinstance(username, str) or not isinstance(color, str):
        raise ProtocolError(
            'join_accepted.username and join_accepted.color must be strings'
        )
    if not isinstance(players_raw, list):
        raise ProtocolError('join_accepted.players must be a list')
    players = [parse_player_info(item) for item in players_raw]
    return JoinAccepted(username, color, players)


def parse_error_message(data: Dict[str, Any]) -> ErrorMessage:
    code = data.get('code')
    message = data.get('message')
    if not isinstance(code, str) or not isinstance(message, str):
        raise ProtocolError('error.code and error.message must be strings')
    return ErrorMessage(code, message)


def parse_client_message(raw_message: str) -> ClientMessage:
    try:
        data = decode_message(raw_message)
    except (TypeError, ValueError) as error:
        raise ProtocolError('message must be a JSON object') from error

    message_type = data.get('type')
    if message_type == JoinRequest.TYPE:
        return parse_join_request(data)
    if message_type == MoveRequest.TYPE:
        return parse_move_request(data)
    raise ProtocolError(
        'unsupported message type: {}'.format(message_type)
    )


def parse_server_message(raw_message: str) -> ServerMessage:
    try:
        data = decode_message(raw_message)
    except (TypeError, ValueError) as error:
        raise ProtocolError('message must be a JSON object') from error

    message_type = data.get('type')
    if message_type == JoinAccepted.TYPE:
        return parse_join_accepted(data)
    if message_type == ErrorMessage.TYPE:
        return parse_error_message(data)
    raise ProtocolError(
        'unsupported server message type: {}'.format(message_type)
    )


def message_to_dict(message: Any) -> Dict[str, Any]:
    if hasattr(message, 'to_dict'):
        return message.to_dict()
    if isinstance(message, dict):
        return message
    raise TypeError('unsupported message object')
