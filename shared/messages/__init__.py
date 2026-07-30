"""Protocol message models and parsers.

Models live in client_messages / server_messages.
Validation and JSON decoding live in parsers.
"""

from shared.messages.client_messages import JoinRequest, MoveRequest, PlayRequest
from shared.messages.errors import ProtocolError
from shared.messages.parsers import (
    ClientMessage,
    ServerMessage,
    message_to_dict,
    parse_client_message,
    parse_disconnect_countdown,
    parse_error_message,
    parse_join_accepted,
    parse_join_request,
    parse_match_found,
    parse_move_request,
    parse_no_match,
    parse_play_request,
    parse_player_info,
    parse_queue_status,
    parse_rating_update,
    parse_server_message,
)
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
from shared.messages.types import (
    ALL_CLIENT_MESSAGE_TYPES,
    ALL_SERVER_MESSAGE_TYPES,
    ClientMessageType,
    ServerMessageType,
)

__all__ = [
    'ALL_CLIENT_MESSAGE_TYPES',
    'ALL_SERVER_MESSAGE_TYPES',
    'ClientMessage',
    'ClientMessageType',
    'DisconnectCountdown',
    'ErrorMessage',
    'JoinAccepted',
    'JoinRequest',
    'MatchFound',
    'MoveRequest',
    'NoMatch',
    'PlayRequest',
    'PlayerInfo',
    'ProtocolError',
    'QueueStatus',
    'RatingUpdate',
    'ServerMessage',
    'ServerMessageType',
    'message_to_dict',
    'parse_client_message',
    'parse_disconnect_countdown',
    'parse_error_message',
    'parse_join_accepted',
    'parse_join_request',
    'parse_match_found',
    'parse_move_request',
    'parse_no_match',
    'parse_play_request',
    'parse_player_info',
    'parse_queue_status',
    'parse_rating_update',
    'parse_server_message',
]
