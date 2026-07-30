"""Network-backed chessboard presentation and click-to-move interaction."""

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import pygame

import constants
from client.gui import theme
from model.board import board_from_token_rows
from model.position import Position
from rules.piece_rules import PIECE_RULES


Cell = Tuple[int, int]


def position_to_square(row: int, col: int, board_height: int = 8) -> str:
    return '{}{}'.format(chr(ord('a') + col), board_height - row)


def build_move_command(
    token: str,
    source: Cell,
    destination: Cell,
    board_height: int = 8,
) -> str:
    return '{}{}{}'.format(
        token[0].lower() + token[1].upper(),
        position_to_square(source[0], source[1], board_height),
        position_to_square(destination[0], destination[1], board_height),
    )


def board_to_display(
    row: int,
    col: int,
    board_height: int,
    board_width: int,
    flipped: bool,
) -> Cell:
    if flipped:
        return board_height - 1 - row, board_width - 1 - col
    return row, col


def display_to_board(
    row: int,
    col: int,
    board_height: int,
    board_width: int,
    flipped: bool,
) -> Cell:
    return board_to_display(row, col, board_height, board_width, flipped)


class NetworkBoardView:
    """Renders authoritative server state and emits protocol move strings."""

    def __init__(self, assets_dir: Optional[Path] = None):
        if assets_dir is None:
            assets_dir = Path(__file__).resolve().parents[2] / 'assets'
        self.assets_dir = Path(assets_dir)
        self.pieces_dir = self.assets_dir / 'pieces'
        self.state: Optional[Dict[str, Any]] = None
        self.role: Optional[str] = None
        self.selected: Optional[Cell] = None
        self._state_received_at = pygame.time.get_ticks()
        self._base_board = self._load_board()
        self._board_cache: Dict[int, pygame.Surface] = {}
        self._sprite_cache: Dict[Tuple[str, str, int], List[pygame.Surface]] = {}

    @property
    def flipped(self) -> bool:
        return self.role == constants.PieceColor.BLACK.value

    def set_role(self, role: Optional[str]) -> None:
        self.role = role
        self.selected = None

    def set_state(self, state: Dict[str, Any]) -> None:
        self.state = state
        self._state_received_at = pygame.time.get_ticks()
        if self.selected is None:
            return
        token = self._token_at(self.selected)
        if (
            not token
            or token[:1] != self.role
            or self.selected in self._moving_sources()
            or self.selected in self._jump_cells()
        ):
            self.selected = None

    def clear(self) -> None:
        self.state = None
        self.role = None
        self.selected = None

    def handle_click(
        self,
        position: Tuple[int, int],
        board_rect: pygame.Rect,
    ) -> Tuple[Optional[str], str]:
        if not self.state:
            return None, 'Waiting for the board state.'
        if self.state.get('game_over'):
            return None, 'This game has finished.'
        if self.role == 'viewer':
            return None, 'You are watching this game.'
        if self.role not in constants.VALID_COLORS:
            return None, 'No player seat is assigned.'
        if not board_rect.collidepoint(position):
            self.selected = None
            return None, ''

        height, width = self._dimensions()
        cell_size = max(1, board_rect.width // width)
        display_col = min(width - 1, (position[0] - board_rect.left) // cell_size)
        display_row = min(height - 1, (position[1] - board_rect.top) // cell_size)
        row, col = display_to_board(
            display_row,
            display_col,
            height,
            width,
            self.flipped,
        )
        clicked = (row, col)
        token = self._token_at(clicked)
        moving_sources = self._moving_sources()
        jumping_cells = self._jump_cells()

        if self.selected is None:
            if clicked in moving_sources:
                return None, 'That piece is already moving.'
            if clicked in jumping_cells:
                return None, 'That piece is already jumping.'
            if not token or token == constants.EMPTY_CELL:
                return None, 'Select one of your pieces first.'
            if token[0] != self.role:
                return None, 'Select a piece in your color.'
            self.selected = clicked
            return None, '{} selected'.format(
                position_to_square(row, col, height),
            )

        if clicked == self.selected:
            source_token = self._token_at(clicked)
            self.selected = None
            if not source_token or source_token[0] != self.role:
                return None, 'The selected piece is no longer available.'
            command = build_move_command(
                source_token,
                clicked,
                clicked,
                height,
            )
            return command, 'Jump sent: {}'.format(
                position_to_square(row, col, height),
            )

        if token and token != constants.EMPTY_CELL and token[0] == self.role:
            if clicked in moving_sources:
                return None, 'That piece is already moving.'
            if clicked in jumping_cells:
                return None, 'That piece is already jumping.'
            self.selected = clicked
            return None, '{} selected'.format(
                position_to_square(row, col, height),
            )

        source = self.selected
        source_token = self._token_at(source)
        self.selected = None
        if not source_token or source_token[0] != self.role:
            return None, 'The selected piece is no longer available.'
        command = build_move_command(
            source_token,
            source,
            clicked,
            height,
        )
        return command, 'Move sent: {}'.format(command)

    def draw(
        self,
        surface: pygame.Surface,
        board_rect: pygame.Rect,
        fonts: theme.FontBook,
    ) -> None:
        if not self.state:
            self._draw_empty(surface, board_rect, fonts)
            return

        height, width = self._dimensions()
        cell_size = max(1, board_rect.width // width)
        exact_rect = pygame.Rect(
            board_rect.left,
            board_rect.top,
            cell_size * width,
            cell_size * height,
        )
        board = self._scaled_board(exact_rect.width)
        surface.blit(board, exact_rect)

        self._draw_jump_backgrounds(surface, exact_rect, cell_size)
        self._draw_legal_moves(surface, exact_rect, cell_size)
        self._draw_selection(surface, exact_rect, cell_size)
        self._draw_pieces(surface, exact_rect, cell_size)
        self._draw_coordinates(surface, exact_rect, fonts)
        pygame.draw.rect(
            surface,
            theme.BORDER,
            exact_rect,
            width=2,
            border_radius=5,
        )

        if self.state.get('game_over'):
            overlay = pygame.Surface(exact_rect.size, pygame.SRCALPHA)
            overlay.fill((7, 12, 22, 138))
            surface.blit(overlay, exact_rect)
            banner = pygame.Rect(0, 0, min(360, exact_rect.width - 60), 92)
            banner.center = exact_rect.center
            pygame.draw.rect(
                surface,
                (17, 27, 45),
                banner,
                border_radius=theme.RADIUS_MEDIUM,
            )
            pygame.draw.rect(
                surface,
                theme.ACCENT,
                banner,
                width=2,
                border_radius=theme.RADIUS_MEDIUM,
            )
            label = fonts.get(30, bold=True).render(
                'GAME COMPLETE',
                True,
                theme.TEXT,
            )
            surface.blit(label, label.get_rect(center=banner.center))

    def _draw_empty(
        self,
        surface: pygame.Surface,
        board_rect: pygame.Rect,
        fonts: theme.FontBook,
    ) -> None:
        pygame.draw.rect(
            surface,
            theme.SURFACE,
            board_rect,
            border_radius=theme.RADIUS_MEDIUM,
        )
        pygame.draw.rect(
            surface,
            theme.BORDER,
            board_rect,
            width=1,
            border_radius=theme.RADIUS_MEDIUM,
        )
        label = fonts.get(18).render(
            'The board will appear when the game starts.',
            True,
            theme.TEXT_MUTED,
        )
        surface.blit(label, label.get_rect(center=board_rect.center))

    def _draw_selection(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
    ) -> None:
        if self.selected is None:
            return
        height, width = self._dimensions()
        display_row, display_col = board_to_display(
            self.selected[0],
            self.selected[1],
            height,
            width,
            self.flipped,
        )
        cell = pygame.Rect(
            rect.left + display_col * cell_size,
            rect.top + display_row * cell_size,
            cell_size,
            cell_size,
        )
        overlay = pygame.Surface(cell.size, pygame.SRCALPHA)
        overlay.fill((*theme.ACCENT, 46))
        surface.blit(overlay, cell)
        pygame.draw.rect(surface, theme.ACCENT, cell, width=3)

    def _draw_legal_moves(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
    ) -> None:
        for row, col in self._legal_destinations():
            height, width = self._dimensions()
            display_row, display_col = board_to_display(
                row,
                col,
                height,
                width,
                self.flipped,
            )
            center = (
                rect.left + display_col * cell_size + cell_size // 2,
                rect.top + display_row * cell_size + cell_size // 2,
            )
            target = self._token_at((row, col))
            if target and target != constants.EMPTY_CELL:
                pygame.draw.circle(
                    surface,
                    theme.ACCENT,
                    center,
                    max(8, cell_size // 2 - 7),
                    width=max(3, cell_size // 18),
                )
            else:
                marker = pygame.Surface(
                    (cell_size, cell_size),
                    pygame.SRCALPHA,
                )
                pygame.draw.circle(
                    marker,
                    (*theme.ACCENT, 150),
                    (cell_size // 2, cell_size // 2),
                    max(5, cell_size // 10),
                )
                surface.blit(
                    marker,
                    (
                        rect.left + display_col * cell_size,
                        rect.top + display_row * cell_size,
                    ),
                )

    def _draw_pieces(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
    ) -> None:
        board = self.state.get('board') or []
        moving_sources = self._moving_sources()
        jumping_cells = self._jump_cells()
        elapsed = pygame.time.get_ticks()
        for row, tokens in enumerate(board):
            for col, token in enumerate(tokens):
                if (
                    token == constants.EMPTY_CELL
                    or len(token) != 2
                    or (row, col) in moving_sources
                    or (row, col) in jumping_cells
                ):
                    continue
                self._blit_piece(
                    surface,
                    token,
                    'idle',
                    row,
                    col,
                    rect,
                    cell_size,
                    elapsed,
                )

        server_time = self._estimated_server_time()
        for motion in self.state.get('active_motions') or []:
            source = motion.get('from') or [0, 0]
            destination = motion.get('to') or source
            duration = max(1, int(motion.get('duration_ms') or 1))
            started = int(motion.get('started_at_ms') or 0)
            progress = max(0.0, min(1.0, (server_time - started) / duration))
            height, width = self._dimensions()
            from_row, from_col = board_to_display(
                int(source[0]),
                int(source[1]),
                height,
                width,
                self.flipped,
            )
            to_row, to_col = board_to_display(
                int(destination[0]),
                int(destination[1]),
                height,
                width,
                self.flipped,
            )
            x = rect.left + (from_col + (to_col - from_col) * progress) * cell_size
            y = rect.top + (from_row + (to_row - from_row) * progress) * cell_size
            token = str(motion.get('piece') or '')
            frames = self._piece_frames(token, 'move', cell_size)
            if not frames:
                continue
            frame = frames[int(elapsed / 120) % len(frames)]
            surface.blit(frame, (int(round(x)), int(round(y))))
        self._draw_jumps(surface, rect, cell_size, elapsed, server_time)

    def _draw_jump_backgrounds(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
    ) -> None:
        if not self.state:
            return
        height, width = self._dimensions()
        for row, col in self._jump_cells():
            display_row, display_col = board_to_display(
                row,
                col,
                height,
                width,
                self.flipped,
            )
            cell = pygame.Rect(
                rect.left + display_col * cell_size,
                rect.top + display_row * cell_size,
                cell_size,
                cell_size,
            )
            overlay = pygame.Surface(cell.size, pygame.SRCALPHA)
            overlay.fill((*theme.BLUE, 48))
            surface.blit(overlay, cell)

    def _draw_jumps(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        cell_size: int,
        elapsed_ms: int,
        server_time: int,
    ) -> None:
        if not self.state:
            return
        height, width = self._dimensions()
        for jump in self.state.get('active_jumps') or []:
            position = jump.get('at')
            if not isinstance(position, (list, tuple)) or len(position) != 2:
                continue
            row, col = int(position[0]), int(position[1])
            display_row, display_col = board_to_display(
                row,
                col,
                height,
                width,
                self.flipped,
            )
            duration = max(1, int(jump.get('duration_ms') or 1))
            started = int(jump.get('started_at_ms') or 0)
            progress = max(0.0, min(1.0, (server_time - started) / duration))
            hop = math.sin(progress * math.pi)
            x = rect.left + display_col * cell_size
            y = (
                rect.top
                + display_row * cell_size
                - hop * cell_size * 0.28
            )
            token = str(jump.get('piece') or '')
            frames = self._piece_frames(token, 'jump', cell_size)
            if not frames:
                continue
            frame = frames[int(elapsed_ms / 120) % len(frames)]
            surface.blit(frame, (int(round(x)), int(round(y))))

    def _blit_piece(
        self,
        surface: pygame.Surface,
        token: str,
        state_name: str,
        row: int,
        col: int,
        rect: pygame.Rect,
        cell_size: int,
        elapsed_ms: int,
    ) -> None:
        frames = self._piece_frames(token, state_name, cell_size)
        if not frames:
            return
        height, width = self._dimensions()
        display_row, display_col = board_to_display(
            row,
            col,
            height,
            width,
            self.flipped,
        )
        frame = frames[int(elapsed_ms / 150) % len(frames)]
        surface.blit(
            frame,
            (
                rect.left + display_col * cell_size,
                rect.top + display_row * cell_size,
            ),
        )

    def _draw_coordinates(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        fonts: theme.FontBook,
    ) -> None:
        height, width = self._dimensions()
        font = fonts.get(max(11, rect.width // 58), bold=True)
        for display_col in range(width):
            _, board_col = display_to_board(
                height - 1,
                display_col,
                height,
                width,
                self.flipped,
            )
            label = font.render(
                chr(ord('a') + board_col),
                True,
                (232, 236, 223),
            )
            surface.blit(
                label,
                (
                    rect.left + display_col * (rect.width // width) + 5,
                    rect.bottom - label.get_height() - 3,
                ),
            )
        for display_row in range(height):
            board_row, _ = display_to_board(
                display_row,
                0,
                height,
                width,
                self.flipped,
            )
            label = font.render(
                str(height - board_row),
                True,
                (232, 236, 223),
            )
            surface.blit(
                label,
                (
                    rect.right - label.get_width() - 5,
                    rect.top + display_row * (rect.height // height) + 3,
                ),
            )

    def _legal_destinations(self) -> Set[Cell]:
        if self.selected is None or not self.state:
            return set()
        try:
            board = board_from_token_rows(self.state.get('board') or [])
            piece = board.piece_at(Position(*self.selected))
            if piece is None:
                return set()
            rule = PIECE_RULES.get(piece.kind)
            if rule is None:
                return set()
            return {
                (position.row, position.col)
                for position in rule.legal_destinations(board, piece)
            }
        except (IndexError, TypeError, ValueError):
            return set()

    def _token_at(self, cell: Cell) -> Optional[str]:
        if not self.state:
            return None
        row, col = cell
        board = self.state.get('board') or []
        if row < 0 or row >= len(board):
            return None
        if col < 0 or col >= len(board[row]):
            return None
        return board[row][col]

    def _dimensions(self) -> Cell:
        if not self.state:
            return 8, 8
        return (
            int(self.state.get('board_height') or 8),
            int(self.state.get('board_width') or 8),
        )

    def _moving_sources(self) -> Set[Cell]:
        if not self.state:
            return set()
        sources: Set[Cell] = set()
        for motion in self.state.get('active_motions') or []:
            source = motion.get('from')
            if isinstance(source, (list, tuple)) and len(source) == 2:
                sources.add((int(source[0]), int(source[1])))
        return sources

    def _jump_cells(self) -> Set[Cell]:
        if not self.state:
            return set()
        cells: Set[Cell] = set()
        for jump in self.state.get('active_jumps') or []:
            position = jump.get('at')
            if isinstance(position, (list, tuple)) and len(position) == 2:
                cells.add((int(position[0]), int(position[1])))
        return cells

    def _estimated_server_time(self) -> int:
        if not self.state:
            return 0
        base = int(self.state.get('server_time_ms') or 0)
        elapsed = max(0, pygame.time.get_ticks() - self._state_received_at)
        return base + elapsed

    def _load_board(self) -> Optional[pygame.Surface]:
        try:
            return pygame.image.load(
                str(self.assets_dir / 'board.png'),
            ).convert()
        except (FileNotFoundError, pygame.error):
            return None

    def _scaled_board(self, size: int) -> pygame.Surface:
        cached = self._board_cache.get(size)
        if cached is not None:
            return cached
        if self._base_board is not None:
            board = pygame.transform.smoothscale(
                self._base_board,
                (size, size),
            )
        else:
            board = self._fallback_board(size)
        self._board_cache[size] = board
        return board

    @staticmethod
    def _fallback_board(size: int) -> pygame.Surface:
        board = pygame.Surface((size, size))
        cell_size = max(1, size // 8)
        light = (204, 187, 160)
        dark = (91, 112, 104)
        for row in range(8):
            for col in range(8):
                pygame.draw.rect(
                    board,
                    light if (row + col) % 2 == 0 else dark,
                    (
                        col * cell_size,
                        row * cell_size,
                        cell_size,
                        cell_size,
                    ),
                )
        return board

    def _piece_frames(
        self,
        token: str,
        state_name: str,
        cell_size: int,
    ) -> List[pygame.Surface]:
        if len(token) != 2:
            return []
        key = (token, state_name, cell_size)
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached
        frames = self._load_piece_frames(token, state_name, cell_size)
        if not frames and state_name != 'idle':
            frames = self._piece_frames(token, 'idle', cell_size)
        self._sprite_cache[key] = frames
        return frames

    def _load_piece_frames(
        self,
        token: str,
        state_name: str,
        cell_size: int,
    ) -> List[pygame.Surface]:
        folder = self.pieces_dir / token / 'states' / state_name / 'sprites'
        if not folder.is_dir():
            return []
        paths = sorted(
            folder.glob('*.png'),
            key=lambda path: int(path.stem) if path.stem.isdigit() else path.stem,
        )
        frames: List[pygame.Surface] = []
        for path in paths:
            try:
                image = pygame.image.load(str(path)).convert_alpha()
                frames.append(
                    pygame.transform.smoothscale(
                        image,
                        (cell_size, cell_size),
                    )
                )
            except pygame.error:
                continue
        return frames
