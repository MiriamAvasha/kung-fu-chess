class ClientMessageType:
    JOIN = 'join'
    PLAY = 'play'
    MOVE = 'move'


class ServerMessageType:
    ERROR = 'error'
    JOIN_ACCEPTED = 'join_accepted'
    QUEUE_STATUS = 'queue_status'
    MATCH_FOUND = 'match_found'
    NO_MATCH = 'no_match'
    DISCONNECT_COUNTDOWN = 'disconnect_countdown'
    RATING_UPDATE = 'rating_update'
    MOVE_RESULT = 'move_result'
    INITIAL_STATE = 'initial_state'
    GAME_STATE = 'game_state'


ALL_SERVER_MESSAGE_TYPES = frozenset(
    getattr(ServerMessageType, name)
    for name in dir(ServerMessageType)
    if name.isupper()
)

ALL_CLIENT_MESSAGE_TYPES = frozenset(
    getattr(ClientMessageType, name)
    for name in dir(ClientMessageType)
    if name.isupper()
)
