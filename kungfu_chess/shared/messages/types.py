class ClientMessageType:
    JOIN = 'join'
    PLAY = 'play'
    CREATE_ROOM = 'create_room'
    JOIN_ROOM = 'join_room'
    MOVE = 'move'


class ServerMessageType:
    ERROR = 'error'
    JOIN_ACCEPTED = 'join_accepted'
    QUEUE_STATUS = 'queue_status'
    MATCH_FOUND = 'match_found'
    NO_MATCH = 'no_match'
    ROOM_CREATED = 'room_created'
    ROOM_JOINED = 'room_joined'
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
