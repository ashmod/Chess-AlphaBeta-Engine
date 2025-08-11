from __future__ import annotations

"""GUI constants for the Chess-AlphaBeta-Engine.

The GUI is intentionally lightweight (no external assets required). Pieces are
rendered using the system font with Unicode chess symbols. If you later add
piece image assets, you can adapt DRAW_PIECES_USING_FONT to False and load
bitmaps instead.
"""

import pygame
from typing import Any, Dict

# Board / window sizing
BOARD_SQUARES = 8
SQUARE_SIZE = 80  # pixels per square (window width becomes 640)
BOARD_SIZE_PX = BOARD_SQUARES * SQUARE_SIZE
RIGHT_PANEL_WIDTH = 320  # widened panel for clearer layout
# Default starting window size (w, h). Increased for roomier UI.
WINDOW_SIZE = (1280, 720)

# Colors (RGB) - warm wood theme (similar to common chess platforms)
# Board squares
COLOR_LIGHT = (240, 217, 181)   # light wood
COLOR_DARK = (181, 136, 99)     # dark wood

# Overlays / status
COLOR_HIGHLIGHT = (246, 246, 140)  # last move highlight (slightly softer)
COLOR_SELECTION = (210, 180, 70)   # selected piece square
COLOR_LEGAL_MOVE_DOT = (40, 40, 40)
COLOR_CHECK = (225, 70, 70)

# UI surfaces
BACKGROUND_COLOR = (46, 41, 38)    # app background behind panels
COLOR_PANEL_BG = (52, 47, 44)      # side panel / modal background
COLOR_TEXT = (245, 244, 240)
COLOR_TEXT_FAINT = (175, 170, 165)

# Piece colors (glyph rendering) – ensure white pieces appear clearly white
PIECE_WHITE_COLOR = (250, 250, 250)
PIECE_BLACK_COLOR = (35, 35, 40)
PIECE_OUTLINE_COLOR_DARK = (28, 28, 30)   # outline for white pieces
PIECE_OUTLINE_COLOR_LIGHT = (235, 235, 235)  # subtle highlight/outline for black pieces

# Buttons (generic) – used where hard-coded grays existed previously
COLOR_BUTTON_BG = (86, 78, 72)
COLOR_BUTTON_BORDER = (158, 148, 140)

# Rendering flags
DRAW_COORDINATES = True
DRAW_PIECES_USING_FONT = True

# Unicode symbols for white and black pieces (python-chess upper = white)
UNICODE_PIECES = {
	'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
	'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
}

# Frame / timing
FPS = 60
AI_MOVE_DELAY_MS = 300  # small delay to make AI move appear natural

# Fonts (initialized lazily). Avoid direct pygame.font.Font type annotation to prevent
# triggering font module import before it's ready (helps on some Windows setups).
_FONT_CACHE: Dict[int, Any] = {}
_MONO_FONT_CACHE: Dict[int, Any] = {}

FONT_AVAILABLE = False  # will be set True after first successful init

def _ensure_font():
	global FONT_AVAILABLE
	if FONT_AVAILABLE:
		return True
	try:
		if not pygame.get_init():
			pygame.init()
		if hasattr(pygame, "font") and not pygame.font.get_init():
			pygame.font.init()
		FONT_AVAILABLE = hasattr(pygame, "font") and pygame.font.get_init()
	except Exception:
		FONT_AVAILABLE = False
	return FONT_AVAILABLE

def get_font(size: int):  # returns pygame.font.Font or raises
	if not _ensure_font():
		raise RuntimeError("Pygame font module unavailable. Reinstall pygame (conda-forge) to enable text rendering.")
	f = _FONT_CACHE.get(size)
	if f is None:
		try:
			f = pygame.font.SysFont("Segoe UI Symbol", size, bold=True)
		except Exception:
			f = pygame.font.Font(None, size)
		_FONT_CACHE[size] = f
	return f

def get_mono_font(size: int):
	if not _ensure_font():
		raise RuntimeError("Pygame font module unavailable. Reinstall pygame (conda-forge) to enable text rendering.")
	f = _MONO_FONT_CACHE.get(size)
	if f is None:
		try:
			f = pygame.font.SysFont("Consolas", size)
		except Exception:
			f = pygame.font.Font(None, size)
		_MONO_FONT_CACHE[size] = f
	return f

