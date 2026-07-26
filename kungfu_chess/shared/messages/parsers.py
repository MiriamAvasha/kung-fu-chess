from typing import Any, Dict, Union

from shared.messages.client_messages import JoinRequest, MoveRequest
from shared.messages.errors import ProtocolError
from shared.messages.server_messages import (
    ErrorMessage,
    JoinAccepted,
    PlayerInfo,
    RatingUpdate,
)
from shared.protocol import decode_message


ClientMessage = Union[JoinRequest, MoveRequest]
ServerMessage = Union[JoinAccepted, ErrorMessage, RatingUpdate]


def parse_player_info(data: Any) -> PlayerInfo:
    if not isinstance(data, dict):
        raise ProtocolError('player must be an object')
    username = data.get('username')
    color = data.get('color')
    rating = data.get('rating')
    if not isinstance(username, str) or not isinstance(color, str):
        raise ProtocolError('player.username and player.color must be strings')
    if not isinstance(rating, int):
        raise ProtocolError('player.rating must be an integer')
    return PlayerInfo(username, color, rating)


def parse_join_request(data: Dict[str, Any]) -> JoinRequest:
    username = data.get('username')
    password = data.get('password')
    if not isinstance(username, str):
        raise ProtocolError('join.username must be a string')
    if not isinstance(password, str):
        raise ProtocolError('join.password must be a string')
    return JoinRequest(username, password)


def parse_move_request(data: Dict[str, Any]) -> MoveRequest:
    command = data.get('command')
    if not isinstance(command, str):
        raise ProtocolError('move.command must be a string')
    return MoveRequest(command)


def parse_join_accepted(data: Dict[str, Any]) -> JoinAccepted:
    username = data.get('username')
    color = data.get('color')
    rating = data.get('rating')
    players_raw = data.get('players')
    if not isinstance(username, str) or not isinstance(color, str):
        raise ProtocolError(
            'join_accepted.username and join_accepted.color must be strings'
        )
    if not isinstance(rating, int):
        raise ProtocolError('join_accepted.rating must be an integer')
    if not isinstance(players_raw, list):
        raise ProtocolError('join_accepted.players must be a list')
    players = [parse_player_info(item) for item in players_raw]
    return JoinAccepted(username, color, rating, players)


def parse_rating_update(data: Dict[str, Any]) -> RatingUpdate:
    winner = data.get('winner')
    loser = data.get('loser')
    ratings = data.get('ratings')
    if not isinstance(winner, str) or not isinstance(loser, str):
        raise ProtocolError(
            'rating_update.winner and rating_update.loser must be strings'
        )
    if not isinstance(ratings, dict):
        raise ProtocolError('rating_update.ratings must be an object')
    normalized = {}
    for key, value in ratings.items():
        if not isinstance(key, str) or not isinstance(value, int):
            raise ProtocolError(
                'rating_update.ratings must map usernames to integers'
            )
        normalized[key] = value
    return RatingUpdate(winner, loser, normalized)


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
    if message_type == RatingUpdate.TYPE:
        return parse_rating_update(data)
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
