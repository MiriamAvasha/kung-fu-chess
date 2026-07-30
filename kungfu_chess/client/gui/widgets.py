"""Reusable Pygame widgets used by the graphical client."""

from typing import Iterable, List, Optional, Tuple

import pygame

from client.gui import theme


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: Tuple[int, int],
    color=theme.TEXT,
    anchor: str = 'topleft',
) -> pygame.Rect:
    rendered = font.render(str(text), True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, position)
    surface.blit(rendered, rect)
    return rect


def wrap_lines(
    font: pygame.font.Font,
    text: str,
    max_width: int,
) -> List[str]:
    words = str(text).split()
    if not words:
        return ['']
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = '{} {}'.format(current, word)
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    rect: pygame.Rect,
    color=theme.TEXT_MUTED,
    line_gap: int = 5,
) -> int:
    y = rect.top
    for line in wrap_lines(font, text, rect.width):
        draw_text(surface, font, line, (rect.left, y), color)
        y += font.get_linesize() + line_gap
    return y


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color=theme.SURFACE,
    border_color=theme.BORDER_SOFT,
    radius: int = theme.RADIUS_LARGE,
    shadow: bool = True,
) -> None:
    if shadow:
        shadow_surface = pygame.Surface(
            (rect.width + 20, rect.height + 20),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(
            shadow_surface,
            theme.SHADOW,
            shadow_surface.get_rect().inflate(-8, -8),
            border_radius=radius + 4,
        )
        surface.blit(shadow_surface, (rect.left - 10, rect.top - 4))
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(
        surface,
        border_color,
        rect,
        width=1,
        border_radius=radius,
    )


def draw_button(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    label: str,
    mouse_position: Tuple[int, int],
    variant: str = 'primary',
    enabled: bool = True,
    subtitle: Optional[str] = None,
) -> None:
    hovered = enabled and rect.collidepoint(mouse_position)
    if not enabled:
        background = theme.SURFACE_ALT
        foreground = theme.TEXT_FAINT
        border = theme.BORDER_SOFT
    elif variant == 'primary':
        background = theme.ACCENT_HOVER if hovered else theme.ACCENT
        foreground = theme.BACKGROUND_TOP
        border = background
    elif variant == 'danger':
        background = (91, 42, 53) if hovered else (72, 35, 45)
        foreground = theme.ERROR
        border = (124, 57, 70)
    elif variant == 'blue':
        background = (48, 83, 137) if hovered else theme.BLUE_DARK
        foreground = (226, 237, 255)
        border = (68, 105, 163)
    else:
        background = theme.SURFACE_HOVER if hovered else theme.SURFACE_ALT
        foreground = theme.TEXT
        border = theme.BORDER

    pygame.draw.rect(
        surface,
        background,
        rect,
        border_radius=theme.RADIUS_SMALL,
    )
    pygame.draw.rect(
        surface,
        border,
        rect,
        width=1,
        border_radius=theme.RADIUS_SMALL,
    )
    if subtitle:
        draw_text(
            surface,
            font,
            label,
            (rect.left + 18, rect.top + 12),
            foreground,
        )
        small_font = pygame.font.Font(
            pygame.font.match_font('segoeui')
            or pygame.font.match_font('arial'),
            max(12, font.get_height() - 7),
        )
        draw_text(
            surface,
            small_font,
            subtitle,
            (rect.left + 18, rect.bottom - 24),
            theme.TEXT_MUTED if enabled else theme.TEXT_FAINT,
        )
    else:
        draw_text(
            surface,
            font,
            label,
            rect.center,
            foreground,
            anchor='center',
        )


def draw_pill(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: Tuple[int, int],
    color=theme.ACCENT,
) -> pygame.Rect:
    label = font.render(text, True, color)
    rect = label.get_rect(topleft=(position[0] + 10, position[1] + 6))
    pill = pygame.Rect(
        position[0],
        position[1],
        rect.width + 20,
        rect.height + 12,
    )
    fill = pygame.Surface(pill.size, pygame.SRCALPHA)
    pygame.draw.rect(
        fill,
        (*color, 26),
        fill.get_rect(),
        border_radius=pill.height // 2,
    )
    surface.blit(fill, pill)
    surface.blit(label, rect)
    return pill


def draw_spinner(
    surface: pygame.Surface,
    center: Tuple[int, int],
    radius: int,
    elapsed_ms: int,
) -> None:
    start = (elapsed_ms / 650.0) * 6.283185307
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    pygame.draw.circle(surface, theme.BORDER, center, radius, width=4)
    pygame.draw.arc(
        surface,
        theme.ACCENT,
        rect,
        start,
        start + 2.0,
        width=4,
    )


class TextInput:
    """A focused, keyboard-driven input field with optional masking."""

    def __init__(
        self,
        label: str,
        placeholder: str = '',
        password: bool = False,
        max_length: int = 64,
    ):
        self.label = label
        self.placeholder = placeholder
        self.password = password
        self.max_length = max_length
        self.text = ''
        self.active = False
        self.rect = pygame.Rect(0, 0, 0, 0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type != pygame.KEYDOWN or not self.active:
            return False
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return True
        if event.key in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
            return False
        if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            pasted = _clipboard_text()
            if pasted:
                remaining = self.max_length - len(self.text)
                self.text += pasted[:remaining]
            return True
        if event.unicode and event.unicode.isprintable():
            remaining = self.max_length - len(self.text)
            if remaining > 0:
                self.text += event.unicode[:remaining]
            return True
        return False

    def draw(
        self,
        surface: pygame.Surface,
        fonts: theme.FontBook,
        rect: pygame.Rect,
    ) -> None:
        self.rect = rect
        label_font = fonts.get(14, bold=True)
        value_font = fonts.get(18)
        draw_text(
            surface,
            label_font,
            self.label,
            (rect.left, rect.top - 25),
            theme.TEXT_MUTED,
        )
        background = theme.SURFACE_ALT if self.active else (27, 40, 63)
        border = theme.ACCENT if self.active else theme.BORDER
        pygame.draw.rect(
            surface,
            background,
            rect,
            border_radius=theme.RADIUS_SMALL,
        )
        pygame.draw.rect(
            surface,
            border,
            rect,
            width=2 if self.active else 1,
            border_radius=theme.RADIUS_SMALL,
        )

        shown = '*' * len(self.text) if self.password else self.text
        if shown:
            color = theme.TEXT
            value = shown
        else:
            color = theme.TEXT_FAINT
            value = self.placeholder
        value_rect = draw_text(
            surface,
            value_font,
            value,
            (rect.left + 16, rect.centery),
            color,
            anchor='midleft',
        )
        if self.active and (pygame.time.get_ticks() // 500) % 2 == 0:
            caret_x = min(rect.right - 14, value_rect.right + 2)
            pygame.draw.line(
                surface,
                theme.ACCENT,
                (caret_x, rect.top + 14),
                (caret_x, rect.bottom - 14),
                width=2,
            )


def _clipboard_text() -> str:
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
        if not raw:
            return ''
        if isinstance(raw, bytes):
            return raw.decode('utf-8', errors='ignore').replace('\x00', '').strip()
        return str(raw).strip()
    except pygame.error:
        return ''
