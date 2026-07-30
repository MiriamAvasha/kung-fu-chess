"""Polished Pygame desktop client backed by the WebSocket game server."""

import asyncio
import contextlib
import time
from typing import Any, Coroutine, Dict, List, Optional, Set, Tuple

import pygame
from websockets.exceptions import ConnectionClosed

from client.gui import theme
from client.gui.board_view import NetworkBoardView
from client.gui.widgets import (
    TextInput,
    draw_button,
    draw_panel,
    draw_pill,
    draw_spinner,
    draw_text,
    draw_wrapped_text,
)
from client.network import DEFAULT_URI, GameConnection
from shared.messages.client_messages import (
    CreateRoomRequest,
    JoinRequest,
    JoinRoomRequest,
    MoveRequest,
    PlayRequest,
)
from shared.messages.types import ServerMessageType
from shared.password import validate_password
from shared.protocol import decode_message
from shared.username import validate_username


class Screen:
    LOGIN = 'login'
    HOME = 'home'
    JOIN_ROOM = 'join_room'
    WAITING = 'waiting'
    ROOM = 'room'
    GAME = 'game'


REASON_LABELS = {
    'ok': 'Move accepted.',
    'wrong_color': 'That piece belongs to the other player.',
    'piece_mismatch': 'The board changed before the move arrived.',
    'empty_source': 'There is no piece on that square.',
    'illegal_move': 'That move is not legal.',
    'illegal_piece_move': 'That piece cannot move to the selected square.',
    'friendly_destination': 'One of your pieces already occupies that square.',
    'outside_board': 'Choose a square inside the board.',
    'motion_in_progress': 'That piece is already moving.',
    'jump_in_progress': 'That piece is currently jumping.',
    'long_rest': 'That piece is recovering.',
    'route_conflict': 'Another piece is crossing that route.',
    'game_over': 'The game has already finished.',
}


class GuiClientApp:
    """Owns the window, UI state, and one WebSocket connection."""

    def __init__(self, uri: str = DEFAULT_URI):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption('Kung Fu Chess — Online')
        self.display_surface = pygame.display.set_mode(
            theme.WINDOW_SIZE,
            pygame.RESIZABLE,
        )
        self.window = pygame.Surface(theme.DESIGN_SIZE).convert()
        self.viewport_rect = pygame.Rect(
            (0, 0),
            self.display_surface.get_size(),
        )
        self.viewport_scale = 1.0
        self._update_viewport()
        self.clock = pygame.time.Clock()
        self.fonts = theme.FontBook()
        self.uri = uri
        self.running = True
        self.screen_name = Screen.LOGIN
        self.background = theme.make_background(theme.DESIGN_SIZE)
        self.mouse_position = (0, 0)
        self.hitboxes: Dict[str, pygame.Rect] = {}

        self.username_input = TextInput(
            'USERNAME',
            'Choose a username',
            max_length=20,
        )
        self.password_input = TextInput(
            'PASSWORD',
            'At least 4 characters',
            password=True,
            max_length=64,
        )
        self.room_input = TextInput(
            'ROOM CODE',
            'Paste or type a room code',
            max_length=24,
        )
        self.username_input.active = True

        self.connection: Optional[GameConnection] = None
        self.receiver_task: Optional[asyncio.Task] = None
        self.tasks: Set[asyncio.Task] = set()
        self.connecting = False

        self.username = ''
        self.rating = 1200
        self.room_id: Optional[str] = None
        self.role: Optional[str] = None
        self.players: List[Dict[str, Any]] = []
        self.session_kind = ''
        self.status = 'Ready'
        self.status_tone = theme.TEXT_MUTED
        self.board = NetworkBoardView()
        self.board_rect = pygame.Rect(0, 0, 0, 0)

        self.toast_message = ''
        self.toast_color = theme.TEXT
        self.toast_until = 0.0

    async def run(self) -> None:
        """Run UI and network work together without terminal input."""
        try:
            while self.running:
                self._handle_events()
                self._draw()
                self._present()
                pygame.display.flip()
                self.clock.tick(theme.FPS)
                await asyncio.sleep(0)
        finally:
            await self._shutdown()

    def _handle_events(self) -> None:
        self.mouse_position = self._display_to_logical(
            pygame.mouse.get_pos(),
        )
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.VIDEORESIZE:
                width = max(theme.MIN_WINDOW_SIZE[0], event.w)
                height = max(theme.MIN_WINDOW_SIZE[1], event.h)
                self.display_surface = pygame.display.set_mode(
                    (width, height),
                    pygame.RESIZABLE,
                )
                self._update_viewport()
                continue

            event = self._event_to_logical(event)

            if self.screen_name == Screen.LOGIN:
                self._handle_login_event(event)
            elif self.screen_name == Screen.HOME:
                self._handle_home_event(event)
            elif self.screen_name == Screen.JOIN_ROOM:
                self._handle_join_room_event(event)
            elif self.screen_name in (Screen.WAITING, Screen.ROOM):
                self._handle_waiting_event(event)
            elif self.screen_name == Screen.GAME:
                self._handle_game_event(event)

    def _update_viewport(self) -> None:
        display_width, display_height = self.display_surface.get_size()
        design_width, design_height = theme.DESIGN_SIZE
        self.viewport_scale = min(
            display_width / float(design_width),
            display_height / float(design_height),
        )
        scaled_width = max(1, int(round(design_width * self.viewport_scale)))
        scaled_height = max(1, int(round(design_height * self.viewport_scale)))
        self.viewport_rect = pygame.Rect(
            (display_width - scaled_width) // 2,
            (display_height - scaled_height) // 2,
            scaled_width,
            scaled_height,
        )

    def _display_to_logical(
        self,
        position: Tuple[int, int],
    ) -> Tuple[int, int]:
        if not self.viewport_rect.collidepoint(position):
            return -10000, -10000
        return (
            int((position[0] - self.viewport_rect.left) / self.viewport_scale),
            int((position[1] - self.viewport_rect.top) / self.viewport_scale),
        )

    def _event_to_logical(
        self,
        event: pygame.event.Event,
    ) -> pygame.event.Event:
        if not hasattr(event, 'pos'):
            return event
        attributes = event.dict.copy()
        attributes['pos'] = self._display_to_logical(event.pos)
        return pygame.event.Event(event.type, attributes)

    def _present(self) -> None:
        self.display_surface.fill(theme.BACKGROUND_TOP)
        if self.viewport_rect.size == theme.DESIGN_SIZE:
            scaled = self.window
        else:
            scaled = pygame.transform.smoothscale(
                self.window,
                self.viewport_rect.size,
            )
        self.display_surface.blit(scaled, self.viewport_rect)

    def _handle_login_event(self, event: pygame.event.Event) -> None:
        self.username_input.handle_event(event)
        self.password_input.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.username_input.active = not self.username_input.active
                self.password_input.active = not self.username_input.active
            elif event.key == pygame.K_RETURN:
                self._submit_login()
            elif event.key == pygame.K_ESCAPE:
                self.running = False
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self._clicked('login', event.pos)
        ):
            self._submit_login()

    def _handle_home_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._spawn(self._disconnect_to_login())
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self._clicked('ranked', event.pos):
            self._start_ranked()
        elif self._clicked('create_room', event.pos):
            self._create_room()
        elif self._clicked('join_room', event.pos):
            self.room_input.text = ''
            self.room_input.active = True
            self.screen_name = Screen.JOIN_ROOM
        elif self._clicked('logout', event.pos):
            self._spawn(self._disconnect_to_login())

    def _handle_join_room_event(self, event: pygame.event.Event) -> None:
        self.room_input.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._join_room()
            elif event.key == pygame.K_ESCAPE:
                self.screen_name = Screen.HOME
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self._clicked('join_submit', event.pos):
            self._join_room()
        elif self._clicked('join_back', event.pos):
            self.screen_name = Screen.HOME
        elif self._clicked('logout', event.pos):
            self._spawn(self._disconnect_to_login())

    def _handle_waiting_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self._clicked('copy_room', event.pos):
            self._copy_room_code()
        elif (
            self._clicked('disconnect', event.pos)
            or self._clicked('logout', event.pos)
        ):
            self._spawn(self._disconnect_to_login())

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.board.selected = None
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self._clicked('copy_room', event.pos):
            self._copy_room_code()
            return
        if (
            self._clicked('disconnect', event.pos)
            or self._clicked('logout', event.pos)
        ):
            self._spawn(self._disconnect_to_login())
            return
        command, feedback = self.board.handle_click(event.pos, self.board_rect)
        if feedback:
            self.status = feedback
            self.status_tone = theme.TEXT_MUTED
        if command:
            self._spawn(
                self._send_message(MoveRequest(command).to_dict()),
            )

    def _submit_login(self) -> None:
        if self.connecting:
            return
        valid_username, username = validate_username(
            self.username_input.text,
        )
        if not valid_username:
            self._toast('Username: {}'.format(username), theme.ERROR)
            return
        valid_password, password = validate_password(
            self.password_input.text,
        )
        if not valid_password:
            self._toast('Password: {}'.format(password), theme.ERROR)
            return
        self.connecting = True
        self._spawn(self._connect_and_login(username, password))

    def _start_ranked(self) -> None:
        self._reset_session()
        self.session_kind = 'Ranked matchmaking'
        self.status = 'Finding a similarly rated opponent...'
        self.status_tone = theme.ACCENT
        self.screen_name = Screen.WAITING
        self._spawn(self._send_message(PlayRequest().to_dict()))

    def _create_room(self) -> None:
        self._reset_session()
        self.session_kind = 'Casual room'
        self.status = 'Creating your private room...'
        self.status_tone = theme.ACCENT
        self.screen_name = Screen.WAITING
        self._spawn(self._send_message(CreateRoomRequest().to_dict()))

    def _join_room(self) -> None:
        room_id = self.room_input.text.strip()
        if not room_id:
            self._toast('Enter a room code first.', theme.ERROR)
            return
        self._reset_session()
        self.session_kind = 'Casual room'
        self.status = 'Joining room {}...'.format(room_id)
        self.status_tone = theme.ACCENT
        self.screen_name = Screen.WAITING
        self._spawn(
            self._send_message(JoinRoomRequest(room_id).to_dict()),
        )

    async def _connect_and_login(
        self,
        username: str,
        password: str,
    ) -> None:
        self.status = 'Connecting to the game server...'
        try:
            if self.connection is None:
                self.connection = await GameConnection.open(self.uri)
            await self.connection.send_message(
                JoinRequest(username, password).to_dict(),
            )
            raw_message = await self.connection.receive_raw()
            message = decode_message(raw_message)
            if message.get('type') != ServerMessageType.JOIN_ACCEPTED:
                self._handle_login_failure(message)
                return

            self.username = str(message.get('username') or username)
            self.rating = int(message.get('rating') or 1200)
            self.username_input.text = self.username
            self.password_input.text = ''
            self.screen_name = Screen.HOME
            self.status = 'Connected'
            self.status_tone = theme.SUCCESS
            self._toast(
                'Welcome, {}.'.format(self.username),
                theme.SUCCESS,
            )
            self.receiver_task = asyncio.create_task(self._receive_messages())
        except (ConnectionClosed, OSError, ValueError) as error:
            await self._discard_connection()
            self._toast(
                'Could not connect: {}'.format(error),
                theme.ERROR,
                seconds=5,
            )
        finally:
            self.connecting = False

    def _handle_login_failure(self, message: Dict[str, Any]) -> None:
        if message.get('type') == ServerMessageType.ERROR:
            detail = message.get('message') or 'Login failed.'
        else:
            detail = 'The server returned an unexpected response.'
        self._toast(str(detail), theme.ERROR, seconds=5)

    async def _receive_messages(self) -> None:
        connection = self.connection
        if connection is None:
            return
        try:
            async for raw_message in connection.incoming():
                try:
                    message = decode_message(raw_message)
                except (TypeError, ValueError):
                    self._toast('The server sent invalid data.', theme.ERROR)
                    continue
                self._handle_server_message(message)
        except ConnectionClosed:
            if self.running:
                self._toast('Connection to the server was closed.', theme.ERROR)
        except OSError as error:
            if self.running:
                self._toast('Network error: {}'.format(error), theme.ERROR)
        finally:
            if self.running and self.connection is connection:
                self.connection = None
                self.screen_name = Screen.LOGIN
                self._reset_session()
                self._clear_account()

    def _handle_server_message(self, message: Dict[str, Any]) -> None:
        message_type = message.get('type')
        if message_type == ServerMessageType.QUEUE_STATUS:
            self.screen_name = Screen.WAITING
            self.status = 'Searching within ELO +/- {}...'.format(
                message.get('elo_range', 100),
            )
            self.status_tone = theme.ACCENT
        elif message_type == ServerMessageType.MATCH_FOUND:
            self._handle_match_found(message)
        elif message_type == ServerMessageType.NO_MATCH:
            self.screen_name = Screen.HOME
            self._toast(
                str(message.get('message') or 'No opponent was found.'),
                theme.WARNING,
            )
        elif message_type == ServerMessageType.ROOM_CREATED:
            self._handle_room_update(message, created=True)
        elif message_type == ServerMessageType.ROOM_JOINED:
            self._handle_room_update(message, created=False)
        elif message_type in (
            ServerMessageType.INITIAL_STATE,
            ServerMessageType.GAME_STATE,
        ):
            self._handle_game_state(message)
        elif message_type == ServerMessageType.MOVE_RESULT:
            self._handle_move_result(message)
        elif message_type == ServerMessageType.DISCONNECT_COUNTDOWN:
            self.status = '{} disconnected — {}s remaining'.format(
                message.get('username', 'Opponent'),
                message.get('seconds_remaining', 0),
            )
            self.status_tone = theme.WARNING
        elif message_type == ServerMessageType.RATING_UPDATE:
            self._handle_rating_update(message)
        elif message_type == ServerMessageType.ERROR:
            self._handle_error(message)

    def _handle_match_found(self, message: Dict[str, Any]) -> None:
        self.room_id = message.get('room_id')
        self.role = message.get('color')
        self.players = list(message.get('players') or [])
        self.session_kind = 'Ranked match'
        self.board.set_role(self.role)
        self.status = 'Opponent found. Preparing the board...'
        self.status_tone = theme.SUCCESS
        self.screen_name = Screen.WAITING

    def _handle_room_update(
        self,
        message: Dict[str, Any],
        created: bool,
    ) -> None:
        self.room_id = message.get('room_id')
        self.role = message.get('role')
        self.players = list(message.get('members') or [])
        self.session_kind = 'Casual room'
        self.board.set_role(self.role)
        game_started = bool(message.get('game_started'))
        if game_started:
            self.status = 'Game ready. Loading the board...'
            self.status_tone = theme.SUCCESS
            self.screen_name = Screen.WAITING
        else:
            self.screen_name = Screen.ROOM
            self.status = (
                'Room created. Share the code with your opponent.'
                if created
                else 'Connected. Waiting for the second player.'
            )
            self.status_tone = theme.ACCENT

    def _handle_game_state(self, message: Dict[str, Any]) -> None:
        state = message.get('state')
        if not isinstance(state, dict):
            self._toast('The board state is invalid.', theme.ERROR)
            return
        self.board.set_role(self.role)
        self.board.set_state(state)
        self.screen_name = Screen.GAME
        if state.get('game_over'):
            self.status = 'Game complete'
            self.status_tone = theme.ACCENT
        elif self.role == 'viewer':
            self.status = 'Live spectator view'
            self.status_tone = theme.BLUE
        else:
            self.status = 'Select a piece, then choose its destination.'
            self.status_tone = theme.TEXT_MUTED

    def _handle_move_result(self, message: Dict[str, Any]) -> None:
        state = message.get('state')
        if isinstance(state, dict):
            self.board.set_state(state)
        accepted = bool(message.get('accepted'))
        reason = str(message.get('reason') or '')
        command = str(message.get('command') or '')
        is_jump = len(command) >= 6 and command[2:4] == command[4:6]
        if accepted and reason == 'ok' and is_jump:
            self.status = 'Jump accepted.'
        else:
            self.status = REASON_LABELS.get(
                reason,
                'Move accepted.'
                if accepted
                else 'Move rejected: {}'.format(reason),
            )
        self.status_tone = theme.SUCCESS if accepted else theme.ERROR
        if not accepted:
            self._toast(self.status, theme.ERROR)

    def _handle_rating_update(self, message: Dict[str, Any]) -> None:
        ratings = message.get('ratings') or {}
        if self.username in ratings:
            self.rating = int(ratings[self.username])
        winner = message.get('winner') or 'Winner'
        self.status = '{} won — ratings updated'.format(winner)
        self.status_tone = theme.ACCENT
        self._toast(self.status, theme.SUCCESS, seconds=6)

    def _handle_error(self, message: Dict[str, Any]) -> None:
        code = str(message.get('code') or 'error')
        detail = str(message.get('message') or 'Something went wrong.')
        self._toast(detail, theme.ERROR, seconds=5)
        self.status = detail
        self.status_tone = theme.ERROR
        if code in ('room_not_found', 'room_full'):
            self.screen_name = Screen.JOIN_ROOM
            self.room_input.active = True
        elif code in ('not_joined',):
            self.screen_name = Screen.LOGIN

    async def _send_message(self, payload: Dict[str, Any]) -> None:
        if self.connection is None:
            self._toast('Connect to the server first.', theme.ERROR)
            self.screen_name = Screen.LOGIN
            return
        try:
            await self.connection.send_message(payload)
        except (ConnectionClosed, OSError) as error:
            self._toast('Could not send: {}'.format(error), theme.ERROR)
            await self._discard_connection()
            self.screen_name = Screen.LOGIN

    def _draw(self) -> None:
        self.window.blit(self.background, (0, 0))
        self.hitboxes.clear()
        if self.screen_name == Screen.LOGIN:
            self._draw_login()
        elif self.screen_name == Screen.HOME:
            self._draw_home()
        elif self.screen_name == Screen.JOIN_ROOM:
            self._draw_join_room()
        elif self.screen_name in (Screen.WAITING, Screen.ROOM):
            self._draw_waiting()
        elif self.screen_name == Screen.GAME:
            self._draw_game()
        self._draw_toast()

    def _draw_login(self) -> None:
        width, height = self.window.get_size()
        self._draw_brand((72, 58), compact=False)

        title_y = max(200, int(height * 0.28))
        hero_size = 66 if width >= 1180 else 52
        hero_gap = hero_size + 6
        draw_text(
            self.window,
            self.fonts.get(hero_size, bold=True),
            'REAL-TIME CHESS.',
            (74, title_y),
            theme.TEXT,
        )
        draw_text(
            self.window,
            self.fonts.get(hero_size, bold=True),
            'NO WAITING.',
            (74, title_y + hero_gap),
            theme.ACCENT,
        )
        draw_wrapped_text(
            self.window,
            self.fonts.get(18),
            'Move every piece at once, challenge similarly rated players, '
            'or create a private room for friends.',
            pygame.Rect(
                78,
                title_y + hero_gap + 93,
                min(520, width // 2 - 90),
                100,
            ),
            theme.TEXT_MUTED,
            line_gap=7,
        )

        feature_y = title_y + hero_gap + 203
        for color, label in (
            (theme.ACCENT, 'Authoritative online matches'),
            (theme.BLUE, 'Private rooms and spectator mode'),
            (theme.WARNING, 'Live animated piece movement'),
        ):
            pygame.draw.circle(self.window, color, (86, feature_y + 9), 5)
            draw_text(
                self.window,
                self.fonts.get(16),
                label,
                (104, feature_y),
                theme.TEXT_MUTED,
            )
            feature_y += 38

        card_width = min(440, width - 610)
        card = pygame.Rect(
            width - card_width - 70,
            max(90, (height - 590) // 2),
            card_width,
            590,
        )
        draw_panel(self.window, card)
        draw_text(
            self.window,
            self.fonts.get(14, bold=True),
            'WELCOME BACK',
            (card.left + 42, card.top + 42),
            theme.ACCENT,
        )
        draw_text(
            self.window,
            self.fonts.get(32, bold=True),
            'Enter the arena',
            (card.left + 42, card.top + 72),
        )
        draw_wrapped_text(
            self.window,
            self.fonts.get(15),
            'New usernames are registered automatically.',
            pygame.Rect(card.left + 42, card.top + 118, card.width - 84, 48),
        )

        input_rect = pygame.Rect(
            card.left + 42,
            card.top + 190,
            card.width - 84,
            58,
        )
        self.username_input.draw(self.window, self.fonts, input_rect)
        password_rect = input_rect.move(0, 112)
        self.password_input.draw(self.window, self.fonts, password_rect)

        login_rect = pygame.Rect(
            card.left + 42,
            card.top + 424,
            card.width - 84,
            58,
        )
        self._button(
            'login',
            login_rect,
            'SIGN IN & CONNECT' if not self.connecting else 'CONNECTING...',
            variant='primary',
            enabled=not self.connecting,
        )
        if self.connecting:
            draw_spinner(
                self.window,
                (login_rect.left + 28, login_rect.centery),
                9,
                pygame.time.get_ticks(),
            )

        pygame.draw.line(
            self.window,
            theme.BORDER_SOFT,
            (card.left + 42, card.top + 514),
            (card.right - 42, card.top + 514),
        )
        pygame.draw.circle(
            self.window,
            theme.SUCCESS if self.connection else theme.TEXT_FAINT,
            (card.left + 47, card.top + 546),
            5,
        )
        draw_text(
            self.window,
            self.fonts.get(13),
            self.uri,
            (card.left + 61, card.top + 537),
            theme.TEXT_FAINT,
        )

    def _draw_home(self) -> None:
        width, height = self.window.get_size()
        self._draw_top_bar()
        content = pygame.Rect(70, 128, width - 140, height - 180)
        draw_text(
            self.window,
            self.fonts.get(16, bold=True),
            'ONLINE LOBBY',
            (content.left, content.top),
            theme.ACCENT,
        )
        draw_text(
            self.window,
            self.fonts.get(42, bold=True),
            'Choose how you want to play',
            (content.left, content.top + 34),
        )
        draw_text(
            self.window,
            self.fonts.get(17),
            'One server, three ways into the board.',
            (content.left, content.top + 91),
            theme.TEXT_MUTED,
        )

        gap = 22
        card_top = content.top + 145
        card_height = min(360, content.bottom - card_top)
        first_width = int((content.width - gap * 2) * 0.40)
        other_width = (content.width - first_width - gap * 2) // 2
        ranked = pygame.Rect(
            content.left,
            card_top,
            first_width,
            card_height,
        )
        create = pygame.Rect(
            ranked.right + gap,
            card_top,
            other_width,
            card_height,
        )
        join = pygame.Rect(
            create.right + gap,
            card_top,
            other_width,
            card_height,
        )
        self._draw_action_card(
            'ranked',
            ranked,
            '01',
            'RANKED MATCH',
            'Find an opponent within your rating range. Results update ELO.',
            'FIND OPPONENT',
            theme.ACCENT,
            featured=True,
        )
        self._draw_action_card(
            'create_room',
            create,
            '02',
            'CREATE ROOM',
            'Start a private casual game. You take the White seat.',
            'CREATE CODE',
            theme.BLUE,
        )
        self._draw_action_card(
            'join_room',
            join,
            '03',
            'JOIN ROOM',
            'Enter a room code. Join as Black or watch as a spectator.',
            'ENTER CODE',
            theme.WARNING,
        )

    def _draw_join_room(self) -> None:
        width, height = self.window.get_size()
        self._draw_top_bar()
        card = pygame.Rect(0, 0, 520, 440)
        card.center = (width // 2, height // 2 + 30)
        draw_panel(self.window, card)
        draw_text(
            self.window,
            self.fonts.get(14, bold=True),
            'PRIVATE GAME',
            (card.left + 48, card.top + 44),
            theme.BLUE,
        )
        draw_text(
            self.window,
            self.fonts.get(34, bold=True),
            'Join a room',
            (card.left + 48, card.top + 76),
        )
        draw_wrapped_text(
            self.window,
            self.fonts.get(16),
            'Use the code shared by the room creator. The second player '
            'becomes Black; later arrivals can watch live.',
            pygame.Rect(card.left + 48, card.top + 125, card.width - 96, 75),
        )
        field = pygame.Rect(
            card.left + 48,
            card.top + 226,
            card.width - 96,
            60,
        )
        self.room_input.draw(self.window, self.fonts, field)
        submit = pygame.Rect(
            card.left + 48,
            card.top + 326,
            262,
            58,
        )
        back = pygame.Rect(submit.right + 14, submit.top, 148, 58)
        self._button('join_submit', submit, 'JOIN ROOM')
        self._button('join_back', back, 'BACK', variant='secondary')

    def _draw_waiting(self) -> None:
        width, height = self.window.get_size()
        self._draw_top_bar()
        card = pygame.Rect(0, 0, min(700, width - 180), 500)
        card.center = (width // 2, height // 2 + 28)
        draw_panel(self.window, card)
        draw_spinner(
            self.window,
            (card.centerx, card.top + 92),
            25,
            pygame.time.get_ticks(),
        )
        title = (
            'Waiting for an opponent'
            if self.screen_name == Screen.ROOM
            else 'Preparing your match'
        )
        draw_text(
            self.window,
            self.fonts.get(32, bold=True),
            title,
            (card.centerx, card.top + 142),
            anchor='midtop',
        )
        draw_text(
            self.window,
            self.fonts.get(16),
            self.status,
            (card.centerx, card.top + 192),
            self.status_tone,
            anchor='midtop',
        )

        if self.room_id:
            room_box = pygame.Rect(
                card.left + 74,
                card.top + 244,
                card.width - 148,
                92,
            )
            pygame.draw.rect(
                self.window,
                theme.SURFACE_ALT,
                room_box,
                border_radius=theme.RADIUS_MEDIUM,
            )
            draw_text(
                self.window,
                self.fonts.get(12, bold=True),
                'ROOM CODE',
                (room_box.left + 22, room_box.top + 16),
                theme.TEXT_FAINT,
            )
            draw_text(
                self.window,
                self.fonts.get(28, bold=True),
                self.room_id,
                (room_box.left + 22, room_box.top + 42),
                theme.TEXT,
            )
            copy_rect = pygame.Rect(
                room_box.right - 128,
                room_box.top + 20,
                106,
                52,
            )
            self._button(
                'copy_room',
                copy_rect,
                'COPY',
                variant='secondary',
            )

        role_label = self._role_label()
        if role_label:
            pill = draw_pill(
                self.window,
                self.fonts.get(13, bold=True),
                role_label,
                (card.left + 74, card.bottom - 104),
                self._role_color(),
            )
            draw_text(
                self.window,
                self.fonts.get(14),
                self._players_summary(),
                (pill.right + 16, pill.centery),
                theme.TEXT_MUTED,
                anchor='midleft',
            )
        disconnect = pygame.Rect(
            card.right - 234,
            card.bottom - 70,
            160,
            42,
        )
        self._button(
            'disconnect',
            disconnect,
            'CANCEL & LOG OUT',
            variant='danger',
            font_size=11,
        )

    def _draw_game(self) -> None:
        width, height = self.window.get_size()
        self._draw_top_bar()
        margin = 36
        top = 102
        available_height = height - top - margin
        side_width = max(330, min(410, int(width * 0.31)))
        board_size = min(
            available_height - 24,
            width - side_width - margin * 3,
        )
        board_size = max(480, board_size)
        board_size -= board_size % 8

        board_panel = pygame.Rect(
            margin,
            top,
            board_size + 24,
            board_size + 24,
        )
        draw_panel(
            self.window,
            board_panel,
            color=(17, 27, 44),
            radius=theme.RADIUS_MEDIUM,
        )
        self.board_rect = pygame.Rect(
            board_panel.left + 12,
            board_panel.top + 12,
            board_size,
            board_size,
        )
        self.board.draw(self.window, self.board_rect, self.fonts)

        side = pygame.Rect(
            board_panel.right + 24,
            top,
            width - board_panel.right - margin - 24,
            board_panel.height,
        )
        draw_panel(self.window, side)
        draw_text(
            self.window,
            self.fonts.get(12, bold=True),
            self.session_kind.upper() or 'ONLINE GAME',
            (side.left + 28, side.top + 28),
            theme.ACCENT,
        )
        draw_text(
            self.window,
            self.fonts.get(28, bold=True),
            'LIVE BOARD',
            (side.left + 28, side.top + 54),
        )
        role_pill = draw_pill(
            self.window,
            self.fonts.get(12, bold=True),
            self._role_label() or 'Waiting',
            (side.left + 28, side.top + 102),
            self._role_color(),
        )
        if self.room_id:
            draw_text(
                self.window,
                self.fonts.get(11, bold=True),
                'ROOM',
                (side.left + 28, side.top + 158),
                theme.TEXT_FAINT,
            )
            draw_text(
                self.window,
                self.fonts.get(19, bold=True),
                self.room_id,
                (side.left + 28, side.top + 178),
            )
            copy_rect = pygame.Rect(
                side.right - 96,
                side.top + 163,
                64,
                38,
            )
            self._button(
                'copy_room',
                copy_rect,
                'COPY',
                variant='secondary',
                font_size=11,
            )

        pygame.draw.line(
            self.window,
            theme.BORDER_SOFT,
            (side.left + 28, side.top + 224),
            (side.right - 28, side.top + 224),
        )
        draw_text(
            self.window,
            self.fonts.get(12, bold=True),
            'PLAYERS',
            (side.left + 28, side.top + 248),
            theme.TEXT_FAINT,
        )
        player_y = side.top + 278
        for player in self.players[:3]:
            player_y = self._draw_player_row(side, player, player_y)
        if not self.players:
            draw_text(
                self.window,
                self.fonts.get(14),
                'Waiting for roster...',
                (side.left + 28, player_y),
                theme.TEXT_FAINT,
            )
            player_y += 45

        status_rect = pygame.Rect(
            side.left + 24,
            max(player_y + 22, side.bottom - 178),
            side.width - 48,
            92,
        )
        pygame.draw.rect(
            self.window,
            (20, 32, 52),
            status_rect,
            border_radius=theme.RADIUS_SMALL,
        )
        pygame.draw.rect(
            self.window,
            theme.BORDER_SOFT,
            status_rect,
            width=1,
            border_radius=theme.RADIUS_SMALL,
        )
        pygame.draw.circle(
            self.window,
            self.status_tone,
            (status_rect.left + 19, status_rect.top + 22),
            5,
        )
        draw_text(
            self.window,
            self.fonts.get(11, bold=True),
            'GAME STATUS',
            (status_rect.left + 33, status_rect.top + 13),
            theme.TEXT_FAINT,
        )
        draw_wrapped_text(
            self.window,
            self.fonts.get(14),
            self.status,
            pygame.Rect(
                status_rect.left + 18,
                status_rect.top + 39,
                status_rect.width - 36,
                44,
            ),
            self.status_tone,
            line_gap=2,
        )

        disconnect = pygame.Rect(
            side.left + 28,
            side.bottom - 58,
            side.width - 56,
            36,
        )
        self._button(
            'disconnect',
            disconnect,
            'LEAVE GAME & LOG OUT',
            variant='danger',
            font_size=10,
        )
        hint = (
            'View only'
            if self.role == 'viewer'
            else 'Click destination · click same square to jump'
        )
        draw_text(
            self.window,
            self.fonts.get(12),
            hint,
            (side.left + 28, side.bottom - 82),
            theme.TEXT_FAINT,
        )

    def _draw_top_bar(self) -> None:
        width, _ = self.window.get_size()
        self._draw_brand((42, 27), compact=True)
        pygame.draw.line(
            self.window,
            theme.BORDER_SOFT,
            (36, 84),
            (width - 36, 84),
        )
        logout = pygame.Rect(width - 128, 25, 92, 40)
        account_right = logout.left - 18
        connection_x = account_right - 255
        pygame.draw.circle(
            self.window,
            theme.SUCCESS if self.connection else theme.ERROR,
            (connection_x, 43),
            5,
        )
        draw_text(
            self.window,
            self.fonts.get(12, bold=True),
            'ONLINE' if self.connection else 'OFFLINE',
            (connection_x + 12, 35),
            theme.TEXT_MUTED,
        )
        draw_text(
            self.window,
            self.fonts.get(15, bold=True),
            self.username,
            (account_right, 27),
            theme.TEXT,
            anchor='topright',
        )
        draw_text(
            self.window,
            self.fonts.get(12),
            '{} ELO'.format(self.rating),
            (account_right, 49),
            theme.TEXT_FAINT,
            anchor='topright',
        )
        self._button(
            'logout',
            logout,
            'LOG OUT',
            variant='secondary',
            font_size=11,
        )

    def _draw_brand(
        self,
        position: Tuple[int, int],
        compact: bool,
    ) -> None:
        x, y = position
        size = 38 if compact else 48
        logo_rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(
            self.window,
            theme.ACCENT,
            logo_rect,
            border_radius=11,
        )
        draw_text(
            self.window,
            self.fonts.get(24 if compact else 30, bold=True),
            'K',
            logo_rect.center,
            theme.BACKGROUND_TOP,
            anchor='center',
        )
        title_size = 18 if compact else 22
        draw_text(
            self.window,
            self.fonts.get(title_size, bold=True),
            'KUNG FU CHESS',
            (logo_rect.right + 14, logo_rect.top + 3),
        )
        draw_text(
            self.window,
            self.fonts.get(10 if compact else 11, bold=True),
            'ONLINE ARENA',
            (logo_rect.right + 14, logo_rect.top + title_size + 8),
            theme.TEXT_FAINT,
        )

    def _draw_action_card(
        self,
        key: str,
        rect: pygame.Rect,
        number: str,
        title: str,
        description: str,
        action: str,
        accent,
        featured: bool = False,
    ) -> None:
        hovered = rect.collidepoint(self.mouse_position)
        color = theme.SURFACE_HOVER if hovered else theme.SURFACE
        border = accent if hovered or featured else theme.BORDER_SOFT
        draw_panel(
            self.window,
            rect,
            color=color,
            border_color=border,
            radius=theme.RADIUS_LARGE,
        )
        self.hitboxes[key] = rect
        number_rect = pygame.Rect(rect.left + 28, rect.top + 28, 46, 34)
        pygame.draw.rect(
            self.window,
            (*accent[:3],),
            number_rect,
            border_radius=9,
        )
        draw_text(
            self.window,
            self.fonts.get(13, bold=True),
            number,
            number_rect.center,
            theme.BACKGROUND_TOP,
            anchor='center',
        )
        draw_text(
            self.window,
            self.fonts.get(23, bold=True),
            title,
            (rect.left + 28, rect.top + 91),
        )
        draw_wrapped_text(
            self.window,
            self.fonts.get(15),
            description,
            pygame.Rect(
                rect.left + 28,
                rect.top + 135,
                rect.width - 56,
                96,
            ),
            theme.TEXT_MUTED,
            line_gap=5,
        )
        action_rect = pygame.Rect(
            rect.left + 28,
            rect.bottom - 76,
            rect.width - 56,
            48,
        )
        variant = 'primary' if featured else 'secondary'
        draw_button(
            self.window,
            self.fonts.get(13, bold=True),
            action_rect,
            action,
            self.mouse_position,
            variant=variant,
        )

    def _draw_player_row(
        self,
        side: pygame.Rect,
        player: Dict[str, Any],
        y: int,
    ) -> int:
        row = pygame.Rect(side.left + 24, y, side.width - 48, 54)
        pygame.draw.rect(
            self.window,
            (28, 42, 65),
            row,
            border_radius=theme.RADIUS_SMALL,
        )
        color = player.get('color')
        avatar_color = (
            theme.WHITE_PIECE
            if color == 'w'
            else theme.BLACK_PIECE
            if color == 'b'
            else theme.BLUE
        )
        pygame.draw.circle(
            self.window,
            avatar_color,
            (row.left + 23, row.centery),
            12,
        )
        draw_text(
            self.window,
            self.fonts.get(14, bold=True),
            str(player.get('username') or 'Player'),
            (row.left + 45, row.top + 9),
        )
        detail = '{}{}'.format(
            self._role_name(color),
            ' · {} ELO'.format(player.get('rating'))
            if player.get('rating') is not None
            else '',
        )
        draw_text(
            self.window,
            self.fonts.get(11),
            detail,
            (row.left + 45, row.top + 31),
            theme.TEXT_FAINT,
        )
        return row.bottom + 10

    def _draw_toast(self) -> None:
        if not self.toast_message or time.monotonic() >= self.toast_until:
            return
        width, height = self.window.get_size()
        font = self.fonts.get(14, bold=True)
        text_surface = font.render(self.toast_message, True, self.toast_color)
        toast = pygame.Rect(
            0,
            0,
            min(width - 80, text_surface.get_width() + 54),
            52,
        )
        toast.midbottom = (width // 2, height - 24)
        pygame.draw.rect(
            self.window,
            (18, 29, 47),
            toast,
            border_radius=theme.RADIUS_SMALL,
        )
        pygame.draw.rect(
            self.window,
            self.toast_color,
            toast,
            width=1,
            border_radius=theme.RADIUS_SMALL,
        )
        pygame.draw.circle(
            self.window,
            self.toast_color,
            (toast.left + 20, toast.centery),
            5,
        )
        self.window.blit(
            text_surface,
            text_surface.get_rect(
                midleft=(toast.left + 34, toast.centery),
            ),
        )

    def _button(
        self,
        key: str,
        rect: pygame.Rect,
        label: str,
        variant: str = 'primary',
        enabled: bool = True,
        font_size: int = 13,
    ) -> None:
        self.hitboxes[key] = rect
        draw_button(
            self.window,
            self.fonts.get(font_size, bold=True),
            rect,
            label,
            self.mouse_position,
            variant=variant,
            enabled=enabled,
        )

    def _clicked(self, key: str, position: Tuple[int, int]) -> bool:
        rect = self.hitboxes.get(key)
        return bool(rect and rect.collidepoint(position))

    def _role_label(self) -> str:
        return self._role_name(self.role)

    @staticmethod
    def _role_name(role: Optional[str]) -> str:
        if role == 'w':
            return 'White player'
        if role == 'b':
            return 'Black player'
        if role == 'viewer':
            return 'Spectator'
        return ''

    def _role_color(self):
        if self.role == 'w':
            return theme.WHITE_PIECE
        if self.role == 'b':
            return theme.TEXT_MUTED
        if self.role == 'viewer':
            return theme.BLUE
        return theme.ACCENT

    def _players_summary(self) -> str:
        if not self.players:
            return '1 player connected'
        return '{} connected'.format(len(self.players))

    def _copy_room_code(self) -> None:
        if not self.room_id:
            return
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(
                pygame.SCRAP_TEXT,
                self.room_id.encode('utf-8') + b'\x00',
            )
            self._toast('Room code copied.', theme.SUCCESS)
        except pygame.error:
            self._toast(
                'Copy is unavailable. Select the code manually.',
                theme.WARNING,
            )

    def _toast(self, message: str, color, seconds: float = 3.5) -> None:
        self.toast_message = str(message)
        self.toast_color = color
        self.toast_until = time.monotonic() + seconds

    def _reset_session(self) -> None:
        self.room_id = None
        self.role = None
        self.players = []
        self.session_kind = ''
        self.board.clear()
        self.board_rect = pygame.Rect(0, 0, 0, 0)

    def _clear_account(self) -> None:
        self.username = ''
        self.rating = 1200
        self.password_input.text = ''

    def _spawn(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self._task_finished)

    def _task_finished(self, task: asyncio.Task) -> None:
        self.tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.result()
        except Exception as error:
            self._toast('Unexpected error: {}'.format(error), theme.ERROR)

    async def _disconnect_to_login(self) -> None:
        await self._discard_connection()
        self._reset_session()
        self._clear_account()
        self.screen_name = Screen.LOGIN
        self.status = 'Disconnected'
        self.status_tone = theme.TEXT_MUTED

    async def _discard_connection(self) -> None:
        connection = self.connection
        self.connection = None
        receiver = self.receiver_task
        self.receiver_task = None
        if receiver is not None and receiver is not asyncio.current_task():
            receiver.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver
        if connection is not None:
            with contextlib.suppress(Exception):
                await connection.close()

    async def _shutdown(self) -> None:
        for task in tuple(self.tasks):
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        await self._discard_connection()
        pygame.quit()


async def main(uri: str = DEFAULT_URI) -> None:
    """Launch the graphical online client."""
    await GuiClientApp(uri).run()
