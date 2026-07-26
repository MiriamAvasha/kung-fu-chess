from typing import Any, Dict, Union

from shared.messages.client_messages import JoinRequest, MoveRequest, PlayRequest
from shared.messages.errors import ProtocolError
from shared.messages.server_messages import (
    DisconnectCountdown,
    ErrorMessage,
    JoinAccepted,
    MatchFound,
    NoMatch,
    PlayerInfo,
    QueueStatus,
    RatingUpdate,
)
from shared.protocol import decode_message


ClientMessage = Union[JoinRequest, PlayRequest, MoveRequest]
ServerMessage = Union[
    JoinAccepted,
    QueueStatus,
    MatchFound,
    NoMatch,
    DisconnectCountdown,
    ErrorMessage,
    RatingUpdate,
]


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


def parse_play_request(data: Dict[str, Any]) -> PlayRequest:
    return PlayRequest()


def parse_move_request(data: Dict[str, Any]) -> MoveRequest:
    command = data.get('command')
    if not isinstance(command, str):
        raise ProtocolError('move.command must be a string')
    return MoveRequest(command)


def parse_join_accepted(data: Dict[str, Any]) -> JoinAccepted:
    username = data.get('username')
    rating = data.get('rating')
    if not isinstance(username, str):
        raise ProtocolError('join_accepted.username must be a string')
    if not isinstance(rating, int):
        raise ProtocolError('join_accepted.rating must be an integer')
    return JoinAccepted(username, rating)


def parse_queue_status(data: Dict[str, Any]) -> QueueStatus:
    timeout_seconds = data.get('timeout_seconds')
    elo_range = data.get('elo_range')
    if not isinstance(timeout_seconds, int) or not isinstance(elo_range, int):
        raise ProtocolError(
            'queue_status.timeout_seconds and elo_range must be integers'
        )
    return QueueStatus(timeout_seconds, elo_range)


def parse_match_found(data: Dict[str, Any]) -> MatchFound:
    username = data.get('username')
    color = data.get('color')
    rating = data.get('rating')
    players_raw = data.get('players')
    if not isinstance(username, str) or not isinstance(color, str):
        raise ProtocolError(
            'match_found.username and match_found.color must be strings'
        )
    if not isinstance(rating, int):
        raise ProtocolError('match_found.rating must be an integer')
    if not isinstance(players_raw, list):
        raise ProtocolError('match_found.players must be a list')
    players = [parse_player_info(item) for item in players_raw]
    return MatchFound(username, color, rating, players)


def parse_no_match(data: Dict[str, Any]) -> NoMatch:
    message = data.get('message', 'no player found')
    if not isinstance(message, str):
        raise ProtocolError('no_match.message must be a string')
    return NoMatch(message)


def parse_disconnect_countdown(data: Dict[str, Any]) -> DisconnectCountdown:
    username = data.get('username')
    seconds_remaining = data.get('seconds_remaining')
    total_seconds = data.get('total_seconds')
    if not isinstance(username, str):
        raise ProtocolError('disconnect_countdown.username must be a string')
    if not isinstance(seconds_remaining, int) or not isinstance(total_seconds, int):
        raise ProtocolError(
            'disconnect_countdown seconds fields must be integers'
        )
    return DisconnectCountdown(username, seconds_remaining, total_seconds)


def parse_rating_update(data: Dict[str, Any]) -> RatingUpdate:
    winner = data.get('winner')
    loser = data.get('loser')
    ratings = data.get('ratings')
    reason = data.get('reason', 'game_over')
    if not isinstance(winner, str) or not isinstance(loser, str):
        raise ProtocolError(
            'rating_update.winner and rating_update.loser must be strings'
        )
    if not isinstance(ratings, dict):
        raise ProtocolError('rating_update.ratings must be an object')
    if not isinstance(reason, str):
        raise ProtocolError('rating_update.reason must be a string')
    normalized = {}
    for key, value in ratings.items():
        if not isinstance(key, str) or not isinstance(value, int):
            raise ProtocolError(
                'rating_update.ratings must map usernames to integers'
            )
        normalized[key] = value
    return RatingUpdate(winner, loser, normalized, reason)


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
    if message_type == PlayRequest.TYPE:
        return parse_play_request(data)
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
    if message_type == QueueStatus.TYPE:
        return parse_queue_status(data)
    if message_type == MatchFound.TYPE:
        return parse_match_found(data)
    if message_type == NoMatch.TYPE:
        return parse_no_match(data)
    if message_type == DisconnectCountdown.TYPE:
        return parse_disconnect_countdown(data)
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
