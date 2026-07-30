"""Visual system for the desktop WebSocket client."""

from typing import Dict, Tuple

import pygame


DESIGN_SIZE = (1200, 760)
WINDOW_SIZE = DESIGN_SIZE
MIN_WINDOW_SIZE = (720, 456)
FPS = 60

BACKGROUND_TOP = (11, 18, 32)
BACKGROUND_BOTTOM = (20, 31, 52)
SURFACE = (24, 36, 58)
SURFACE_ALT = (31, 45, 70)
SURFACE_HOVER = (38, 54, 82)
BORDER = (58, 76, 106)
BORDER_SOFT = (46, 62, 88)

TEXT = (241, 245, 249)
TEXT_MUTED = (157, 172, 194)
TEXT_FAINT = (112, 129, 153)

ACCENT = (83, 214, 173)
ACCENT_HOVER = (105, 229, 190)
ACCENT_DARK = (17, 83, 69)
BLUE = (93, 155, 255)
BLUE_DARK = (32, 67, 116)
WARNING = (250, 190, 88)
ERROR = (248, 113, 113)
SUCCESS = (74, 222, 128)
WHITE_PIECE = (241, 236, 218)
BLACK_PIECE = (92, 103, 122)

SHADOW = (4, 8, 16, 120)
TRANSPARENT = (0, 0, 0, 0)

RADIUS_LARGE = 24
RADIUS_MEDIUM = 16
RADIUS_SMALL = 10


class FontBook:
    """Small font cache that consistently prefers Segoe UI on Windows."""

    def __init__(self):
        self._cache: Dict[Tuple[int, bool], pygame.font.Font] = {}
        self._font_name = (
            pygame.font.match_font('segoeui')
            or pygame.font.match_font('arial')
        )

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        font = self._cache.get(key)
        if font is None:
            font = pygame.font.Font(self._font_name, size)
            font.set_bold(bold)
            self._cache[key] = font
        return font


def make_background(size: Tuple[int, int]) -> pygame.Surface:
    """Create a reusable dark gradient with restrained accent glows."""
    width, height = size
    surface = pygame.Surface(size)
    denominator = max(1, height - 1)
    for y in range(height):
        ratio = y / denominator
        color = tuple(
            int(top + (bottom - top) * ratio)
            for top, bottom in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM)
        )
        pygame.draw.line(surface, color, (0, y), (width, y))

    glow = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.circle(
        glow,
        (*ACCENT, 18),
        (int(width * 0.12), int(height * 0.08)),
        int(min(width, height) * 0.38),
    )
    pygame.draw.circle(
        glow,
        (*BLUE, 13),
        (int(width * 0.92), int(height * 0.78)),
        int(min(width, height) * 0.42),
    )
    surface.blit(glow, (0, 0))
    return surface
