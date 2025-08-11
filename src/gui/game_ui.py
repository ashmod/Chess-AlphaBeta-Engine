"""Pygame chess GUI and replay viewer.

Features implemented:
 - Interactive board with click-to-move
 - Highlights selected square, legal moves, last move, and check
 - Supports playing Human vs Random or AlphaBeta AI (black side by default)
 - Move list panel with simple controls (Undo, New Game, Quit)
 - Replay viewer to step through recorded games

Limitations / Future improvements:
 - No drag-and-drop yet (click source then destination)
 - No promotion selection UI (auto promotes to queen)
 - No time controls or clock
"""

from __future__ import annotations
import time
import pygame
import chess
import re
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple, Sequence
import os
import glob

from ..core.board import ChessBoard
from ..core.game_io import GameIO
from ..core.rules import ChessRules
from ..ai.random_agent import RandomAgent
from ..ai.alpha_beta import AlphaBetaAgent
from ..ai.evaluation import get_eval_function
from .constants import (
	BOARD_SQUARES, SQUARE_SIZE, BOARD_SIZE_PX, WINDOW_SIZE,
	COLOR_LIGHT, COLOR_DARK, COLOR_HIGHLIGHT, COLOR_SELECTION,
	COLOR_LEGAL_MOVE_DOT, COLOR_CHECK, COLOR_PANEL_BG, COLOR_TEXT,
	COLOR_TEXT_FAINT, DRAW_COORDINATES, UNICODE_PIECES, FPS,
	AI_MOVE_DELAY_MS, BACKGROUND_COLOR, COLOR_BUTTON_BG, COLOR_BUTTON_BORDER,
	PIECE_WHITE_COLOR, PIECE_BLACK_COLOR, PIECE_OUTLINE_COLOR_DARK, PIECE_OUTLINE_COLOR_LIGHT,
	get_font, get_mono_font
)


@dataclass
class MoveRecord:
	ply: int
	uci: str


class ChessGUI:
	def __init__(self, ai: str = 'alphabeta', depth: int = 3, human_plays_white: bool = True, human_plays_black: bool = False, autosave: bool = True, label: str = "Game"):
		# Reuse existing display if already created (App sets RESIZABLE)
		if not pygame.get_init():
			pygame.init()
		if pygame.display.get_surface() is None:
			self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
			pygame.display.set_caption("Chess AlphaBeta Engine")
		else:
			self.screen = pygame.display.get_surface()
		self.clock = pygame.time.Clock()
		self.board = ChessBoard()
		self.selected_square: Optional[int] = None
		self.legal_destinations: List[int] = []
		self.move_history: List[MoveRecord] = []
		self.last_move: Optional[chess.Move] = None
		self.status_message = "White to move"
		self.human_white = human_plays_white
		self.human_black = human_plays_black
		self.autosave = autosave
		self.game_saved = False
		self.label = label
		# Determine AI type for sides
		if ai == 'random':
			self.ai_white = RandomAgent()
			self.ai_black = RandomAgent()
		elif ai == 'mixed_random_alphabeta':
			self.ai_white = RandomAgent()
			self.ai_black = AlphaBetaAgent(depth=depth)
		else:
			self.ai_white = AlphaBetaAgent(depth=depth)
			self.ai_black = AlphaBetaAgent(depth=depth)
		self.pending_ai_move: Optional[Tuple[chess.Move, float]] = None  # (move, ready_time)
		# Schedule initial AI move if white not human
		if not self.human_white:
			first_move = self._compute_ai_move()
			self.pending_ai_move = (first_move, time.time() + AI_MOVE_DELAY_MS / 1000.0)

		# Dynamic layout attributes
		self.square_size = SQUARE_SIZE  # will be recomputed
		self.board_px = BOARD_SIZE_PX
		self.board_left = 0
		self.board_top = 0
		self.panel_left = self.board_px
		self.panel_rect = pygame.Rect(self.panel_left, 0, self.screen.get_width() - self.panel_left, self.screen.get_height())
		self._recompute_layout()
		# Track exit mode: 'done' normal end (game over), 'back' user returned to menu, 'quit' full application quit
		self.exit_mode = 'done'
		# Store button rectangles for click handling (label->Rect)
		self.button_rects: dict[str, pygame.Rect] = {}
		# Confirmation dialog state for mid-game back
		self.confirm_active = False
		self._confirm_result: Optional[bool] = None  # True=yes, False=no
		self.confirm_rect = None
		self.confirm_buttons: dict[str, pygame.Rect] = {}

	def _recompute_layout(self):
		"""Recompute sizes based on current window size.

		Board is as large as possible while leaving a minimum panel width.
		Board centered vertically if extra height.
		"""
		w, h = self.screen.get_size()
		min_panel = 260
		# Maximum square board that fits with panel
		max_board_w = max(0, w - min_panel)
		board_px = min(h, max_board_w)
		min_square = 48  # readability floor
		min_board = min_square * 8
		if board_px < min_board:
			board_px = min_board if w >= min_board + min_panel else max(8 * 32, max_board_w)  # allow shrink smaller only if window small
		# Adjust to multiple of 8
		square_size = max(16, board_px // 8)
		board_px = square_size * 8
		panel_left = board_px
		panel_width = max(140, w - panel_left)
		self.square_size = square_size
		self.board_px = board_px
		self.board_left = 0
		self.board_top = 0 if h <= board_px else (h - board_px) // 2
		self.panel_left = panel_left
		self.panel_rect = pygame.Rect(self.panel_left, 0, panel_width, h)

	# ------------------- Main Loop -------------------
	def run(self):
		running = True
		while running:
			running = self._handle_events()
			self._maybe_trigger_ai()
			self._draw()
			pygame.display.flip()
			self.clock.tick(FPS)
		# Do NOT quit pygame here; App controller manages lifecycle
		return self.exit_mode

	# ------------------- Event Handling -------------------
	def _handle_events(self) -> bool:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.exit_mode = 'quit'
				return False
			if event.type == pygame.VIDEORESIZE:
				self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
				self._recompute_layout()
			if event.type == pygame.KEYDOWN:
				if self.confirm_active:
					if event.key in (pygame.K_ESCAPE, pygame.K_n):
						self.confirm_active = False
					elif event.key in (pygame.K_y, pygame.K_RETURN):
						self.exit_mode = 'back'
						return False
				elif event.key == pygame.K_ESCAPE:
					# Attempt back (with confirmation if needed)
					if self._attempt_back():
						return False
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				mx, my = event.pos
				if self.confirm_active:
					for name, rect in self.confirm_buttons.items():
						if rect.collidepoint(mx, my):
							if name == 'Yes':
								self.exit_mode = 'back'
								return False
							else:
								self.confirm_active = False
								break
					# Ignore other clicks while modal
					continue
				if self._in_board(mx, my):  # inside board
					self._handle_board_click(mx, my)
				else:
					self._handle_panel_click(mx, my)
		# Exit loop if a control set exit_mode
		if self.exit_mode in ('back', 'quit'):
			return False
		return True

	def _in_board(self, mx: int, my: int) -> bool:
		return (self.board_left <= mx < self.board_left + self.board_px and
		        self.board_top <= my < self.board_top + self.board_px)

	def _handle_board_click(self, mx: int, my: int):
		if self.board.board.is_game_over():
			return
		if not self._is_human_turn():
			return  # waiting for AI side
		file = (mx - self.board_left) // self.square_size
		rank = 7 - ((my - self.board_top) // self.square_size)
		square = chess.square(file, rank)
		piece = self.board.board.piece_at(square)
		if self.selected_square is None:
			if piece and piece.color == self.board.board.turn:
				self.selected_square = square
				self.legal_destinations = [m.to_square for m in self.board.board.legal_moves if m.from_square == square]
		else:
			# Attempt move
			if square == self.selected_square:
				# deselect
				self.selected_square = None
				self.legal_destinations = []
				return
			move = chess.Move(self.selected_square, square)
			# Promotion auto-queen
			if (chess.square_rank(self.selected_square) == 6 and chess.square_rank(square) == 7 and
					self.board.board.piece_at(self.selected_square).piece_type == chess.PAWN and
					self.board.board.turn == chess.WHITE):
				move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)
			if (chess.square_rank(self.selected_square) == 1 and chess.square_rank(square) == 0 and
					self.board.board.piece_at(self.selected_square).piece_type == chess.PAWN and
					self.board.board.turn == chess.BLACK):
				move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)

			if move in self.board.board.legal_moves:
				self.board.board.push(move)
				self.last_move = move
				self._record_move(move)
				self._update_status()
				self.selected_square = None
				self.legal_destinations = []
				# schedule AI move
				if not self.board.board.is_game_over() and not self._is_human_turn():
					self.pending_ai_move = (self._compute_ai_move(), time.time() + AI_MOVE_DELAY_MS / 1000.0)
			else:
				# new selection if own piece else clear
				if piece and piece.color == self.board.board.turn:
					self.selected_square = square
					self.legal_destinations = [m.to_square for m in self.board.board.legal_moves if m.from_square == square]
				else:
					self.selected_square = None
					self.legal_destinations = []

	def _handle_panel_click(self, mx: int, my: int):
		# Use stored rects for hit detection
		for name, rect in self.button_rects.items():
			if rect.collidepoint(mx, my):
				if name == 'New Game':
					self._new_game()
				elif name == 'Undo':
					self._undo_move()
				elif name == 'Back':
					self._attempt_back()
				elif name == 'Quit':
					self.exit_mode = 'quit'
					pygame.event.post(pygame.event.Event(pygame.QUIT))
				break

	def _attempt_back(self) -> bool:
		"""Handle a user request to go back. Returns True if loop should exit."""
		# Immediate if game over OR already saved
		if self.board.board.is_game_over() or self.game_saved:
			self.exit_mode = 'back'
			return True
		# Mid-game: show confirmation dialog
		self.confirm_active = True
		self._layout_confirm_dialog()
		return False

	def _layout_confirm_dialog(self):
		w, h = self.screen.get_size()
		modal_w, modal_h = min(420, w - 80), 200
		left = (w - modal_w) // 2
		top = (h - modal_h) // 2
		self.confirm_rect = pygame.Rect(left, top, modal_w, modal_h)
		# Buttons
		btn_w, btn_h = 120, 36
		spacing = 40
		y = top + modal_h - btn_h - 25
		cx = left + modal_w // 2
		yes_rect = pygame.Rect(cx - spacing//2 - btn_w, y, btn_w, btn_h)
		no_rect = pygame.Rect(cx + spacing//2, y, btn_w, btn_h)
		self.confirm_buttons = {'Yes': yes_rect, 'No': no_rect}

	# ------------------- AI handling -------------------
	def _compute_ai_move(self) -> chess.Move:
		# Choose correct AI for side to move
		side = self.board.board.turn
		agent = self.ai_white if side == chess.WHITE else self.ai_black
		return agent.select_move(self.board.board)

	def _maybe_trigger_ai(self):
		if self.pending_ai_move:
			move, ready_time = self.pending_ai_move
			if time.time() >= ready_time:
				if move in self.board.board.legal_moves:  # still valid
					self.board.board.push(move)
					self.last_move = move
					self._record_move(move)
				self.pending_ai_move = None
				self._update_status()
				# Chain next AI move if other side also AI
				if not self.board.board.is_game_over() and not self._is_human_turn():
					self.pending_ai_move = (self._compute_ai_move(), time.time() + AI_MOVE_DELAY_MS / 1000.0)
		else:
			# If idle and it's AI turn schedule immediately (covers resume after undo)
			if not self.board.board.is_game_over() and not self._is_human_turn():
				self.pending_ai_move = (self._compute_ai_move(), time.time() + AI_MOVE_DELAY_MS / 1000.0)

	# ------------------- Game state helpers -------------------
	def _record_move(self, move: chess.Move):
		self.move_history.append(MoveRecord(len(self.move_history) + 1, move.uci()))

	def _update_status(self):
		if self.board.board.is_game_over():
			# Use custom rules: treat stalemate as a win for the side that caused it
			base_reason = ChessRules.get_game_end_reason(self.board)
			if self.board.board.is_stalemate():
				# Determine winner (opposite of side to move)
				winner = 'Black' if self.board.board.turn == chess.WHITE else 'White'
				result = '0-1' if winner == 'Black' else '1-0'
				reason = f"stalemate (awarded win to {winner})"
			else:
				result = self.board.board.result()
				reason = base_reason
			self.status_message = f"Game over: {result} ({reason})"
			# Temporarily override board result for autosave if stalemate variant
			self._final_result_override = result
			if self.autosave and not self.game_saved:
				self._autosave_result()
		else:
			self.status_message = "White to move" if self.board.board.turn else "Black to move"

	def _undo_move(self):
		if self.move_history and not self.pending_ai_move:
			# If last move was AI + player, undo both to revert to player's turn
			if len(self.move_history) >= 2:
				self.board.board.pop()
				self.board.board.pop()
				self.move_history = self.move_history[:-2]
			else:
				self.board.board.pop()
				self.move_history.pop()
			self.last_move = self.board.board.move_stack[-1] if self.board.board.move_stack else None
			self._update_status()

	def _new_game(self):
		self.board = ChessBoard()
		self.selected_square = None
		self.legal_destinations = []
		self.move_history.clear()
		self.last_move = None
		self.pending_ai_move = None
		self.game_saved = False
		if not self.human_white:
			self.pending_ai_move = (self._compute_ai_move(), time.time() + AI_MOVE_DELAY_MS / 1000.0)
		self._update_status()

	# ------------------- Drawing -------------------
	def _draw(self):
		self._draw_board()
		self._draw_panel()
		if self.confirm_active:
			self._draw_confirm_modal()

	def _draw_confirm_modal(self):
		# Dim background
		overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
		overlay.fill((0,0,0,120))
		self.screen.blit(overlay, (0,0))
		if not self.confirm_rect:
			self._layout_confirm_dialog()
		rect = self.confirm_rect
		pygame.draw.rect(self.screen, COLOR_PANEL_BG, rect, border_radius=10)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 2, border_radius=10)
		try:
			font = get_font(20)
			small = get_mono_font(16)
		except Exception:
			return
		# Title centered
		title = "Return to menu?"
		title_txt = font.render(title, True, COLOR_TEXT)
		self.screen.blit(title_txt, title_txt.get_rect(centerx=rect.centerx, y=rect.top + 18))
		# Body text wrapped with padding
		body = ("Current game is not finished and will not be saved. "
				"Are you sure you want to quit this game?")
		max_body_width = rect.width - 40
		try:
			wrapped = wrap_text(body, small, max_body_width)
		except Exception:
			wrapped = [body]
		y = rect.top + 18 + title_txt.get_height() + 12
		for line in wrapped:
			bt = small.render(line, True, COLOR_TEXT_FAINT)
			self.screen.blit(bt, (rect.left + 20, y))
			y += bt.get_height() + 4
		# Draw buttons
		for name, brect in self.confirm_buttons.items():
			pygame.draw.rect(self.screen, COLOR_BUTTON_BG, brect, border_radius=6)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, brect, 2, border_radius=6)
			bf = get_mono_font(18)
			bt = bf.render(name, True, COLOR_TEXT)
			self.screen.blit(bt, bt.get_rect(center=brect.center))

	def _draw_board(self):
		surface = self.screen
		ss = self.square_size
		left = self.board_left
		top = self.board_top
		for rank in range(8):
			for file in range(8):
				square = chess.square(file, 7 - rank)
				is_light = (file + rank) % 2 == 0
				color = COLOR_LIGHT if is_light else COLOR_DARK
				if self.last_move and (square == self.last_move.from_square or square == self.last_move.to_square):
					color = tuple(min(255, c + 30) for c in color)
				# selection highlight
				if self.selected_square == square:
					color = COLOR_SELECTION
				# check highlighting for king
				if self.board.board.is_check():
					king_sq = self.board.board.king(self.board.board.turn)
					if king_sq == square:
						color = COLOR_CHECK
				pygame.draw.rect(surface, color, (left + file * ss, top + rank * ss, ss, ss))

		# legal move dots
		for to_sq in self.legal_destinations:
			tf = chess.square_file(to_sq)
			tr = 7 - chess.square_rank(to_sq)
			center = (left + tf * ss + ss // 2, top + tr * ss + ss // 2)
			pygame.draw.circle(surface, COLOR_LEGAL_MOVE_DOT, center, max(4, ss // 10))

		# pieces
		for square in chess.SQUARES:
			piece = self.board.board.piece_at(square)
			if not piece:
				continue
			file = chess.square_file(square)
			rank = 7 - chess.square_rank(square)
			if self.selected_square == square:
				pass
			if piece:
				self._draw_piece(piece, file, rank)

		if DRAW_COORDINATES:
			self._draw_coordinates()

	def _draw_piece(self, piece: chess.Piece, file: int, rank: int):
		if UNICODE_PIECES and piece.symbol() in UNICODE_PIECES:
			sym = UNICODE_PIECES[piece.symbol()]
		else:
			sym = piece.symbol()
		try:
			ss = self.square_size
			font = get_font(int(ss * 0.7))
			fg = PIECE_WHITE_COLOR if piece.color == chess.WHITE else PIECE_WHITE_COLOR  # fill for both then outline differentiates
			outline_dark = PIECE_OUTLINE_COLOR_DARK
			outline_light = PIECE_OUTLINE_COLOR_LIGHT
			# Base render (white fill)
			base = font.render(sym, True, fg)
			center = (self.board_left + file * ss + ss // 2, self.board_top + rank * ss + ss // 2 + 2)
			# Offsets to create outline effect around glyph
			offsets = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]
			for dx, dy in offsets:
				shade = outline_dark if piece.color == chess.WHITE else outline_light
				shadow = font.render(sym, True, shade)
				rect = shadow.get_rect(center=(center[0]+dx, center[1]+dy))
				self.screen.blit(shadow, rect)
			# Draw inner for black pieces slightly darker fill
			if piece.color == chess.BLACK:
				inner = font.render(sym, True, PIECE_BLACK_COLOR)
				self.screen.blit(inner, inner.get_rect(center=center))
			else:
				self.screen.blit(base, base.get_rect(center=center))
		except Exception:
			# fallback: draw simple circle marker if font unavailable
			color = PIECE_WHITE_COLOR if piece.color == chess.WHITE else PIECE_BLACK_COLOR
			ss = self.square_size
			pygame.draw.circle(self.screen, color, (self.board_left + file * ss + ss // 2, self.board_top + rank * ss + ss // 2), ss // 3, 0)

	def _draw_coordinates(self):
		try:
			font = get_mono_font(14)
		except Exception:
			return  # skip coordinates if font missing
		ss = self.square_size
		for file in range(8):
			txt = font.render(chr(ord('a') + file), True, (50, 50, 50))
			rect = txt.get_rect(center=(self.board_left + file * ss + ss // 2, self.board_top + self.board_px - 10))
			self.screen.blit(txt, rect)
		for rank in range(8):
			txt = font.render(str(rank + 1), True, (50, 50, 50))
			rect = txt.get_rect(center=(self.board_left + 10, self.board_top + (7 - rank) * ss + 10))
			self.screen.blit(txt, rect)

	def _draw_panel(self):
		# Use precomputed panel rect
		panel_rect = self.panel_rect
		pygame.draw.rect(self.screen, COLOR_PANEL_BG, panel_rect)
		try:
			font = get_font(22)
			small = get_mono_font(16)
		except Exception:
			# Draw minimal panel text-free
			return

		# Layout: buttons stacked top-right, info & moves on left side
		# Compute button x relative to panel
		btn_w = RIGHT_BUTTON_WIDTH()
		btn_x_rel = panel_rect.width - btn_w - 20  # relative position from panel left
		btn_y_start = 20
		btn_h = 30
		btn_gap = 10
		btn_names = ["New Game", "Undo", "Back", "Quit"]
		self.button_rects.clear()
		for i, name in enumerate(btn_names):
			by = btn_y_start + i * (btn_h + btn_gap)
			self._draw_button(name, btn_x_rel, by, btn_h)
			self.button_rects[name] = pygame.Rect(self.panel_left + btn_x_rel, by, btn_w, btn_h)

		# Game label top-left
		lbl_txt = small.render(self.label, True, COLOR_TEXT_FAINT)
		self.screen.blit(lbl_txt, (self.panel_left + 20, 20))

		# Status block placed below the tallest of label or button column bottom
		buttons_bottom = btn_y_start + len(btn_names)*(btn_h + btn_gap) - btn_gap
		status_start_y = max(20 + lbl_txt.get_height() + 10, buttons_bottom + 15)
		from .game_ui import wrap_text as _wrap
		try:
			status_lines = _wrap(self.status_message, small, panel_rect.width - 40)
		except Exception:
			status_lines = [self.status_message]
		y = status_start_y
		for line in status_lines:
			txt = small.render(line, True, COLOR_TEXT)
			self.screen.blit(txt, (self.panel_left + 20, y))
			y += txt.get_height() + 2

		# Move list header and entries
		y += 10
		self.screen.blit(font.render("Moves", True, COLOR_TEXT), (self.panel_left + 20, y))
		y += 30
		for i in range(0, len(self.move_history), 2):
			white_move = self.move_history[i].uci if i < len(self.move_history) else ''
			black_move = self.move_history[i+1].uci if i+1 < len(self.move_history) else ''
			line = f"{(i//2)+1:>2}. {white_move:>7} {black_move:>7}"
			txt = small.render(line, True, COLOR_TEXT if i+1 < len(self.move_history) or not self.board.board.turn else COLOR_TEXT_FAINT)
			self.screen.blit(txt, (self.panel_left + 20, y))
			y += txt.get_height() + 2

	# ------------------- Helpers -------------------
	def _is_human_turn(self) -> bool:
		turn = self.board.board.turn
		return (turn == chess.WHITE and self.human_white) or (turn == chess.BLACK and self.human_black)

	def _autosave_result(self):
		try:
			moves = [m.uci() for m in self.board.board.move_stack]
			# Use override result (e.g., stalemate-as-win) if set
			result = getattr(self, '_final_result_override', self.board.board.result())
			white_name = "Human" if self.human_white else (self.ai_white.name if hasattr(self.ai_white, 'name') else 'AI')
			black_name = "Human" if self.human_black else (self.ai_black.name if hasattr(self.ai_black, 'name') else 'AI')
			
			# Format timestamp
			timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
			
			# Create short game mode descriptor
			mode = ""
			if self.human_white and self.human_black:
				mode = "HumanVsHuman"
			elif self.human_white:
				mode = "HumanVsAI"
			elif self.human_black:
				mode = "AIVsHuman"
			else:
				mode = "AIVsAI"
				
			game_data = {
				"moves": moves,
				"result": result,
				"white": white_name,
				"black": black_name,
				"event": self.label,
				"date": timestamp,
				"mode": mode
			}
			
			os.makedirs('replays', exist_ok=True)
			# Create a filename with timestamp and game details, but directly in the replays folder
			filename = os.path.join('replays', f"{timestamp}_{mode}_{result.replace('-', 'v')}.json")
			GameIO.save_replay(game_data, filename)
			self.game_saved = True
		except Exception as e:
			print(f"Error saving replay: {e}")
			pass

	def _draw_button(self, label: str, x: int, y: int, h: int):
		width = RIGHT_BUTTON_WIDTH()
		rect = pygame.Rect(self.panel_left + x, y, width, h)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BG, rect, border_radius=5)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 2, border_radius=5)
		font = get_mono_font(18)
		txt = font.render(label, True, COLOR_TEXT)
		tr = txt.get_rect(center=rect.center)
		self.screen.blit(txt, tr)


class ReplayViewer:
	def __init__(self, replay_data: dict):
		if not pygame.get_init():
			pygame.init()
		if pygame.display.get_surface() is None:
			self.screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
			pygame.display.set_caption("Chess Replay Viewer")
		else:
			self.screen = pygame.display.get_surface()
		self.clock = pygame.time.Clock()
		
		# Store and print the replay data to help with debugging
		self.replay_data = replay_data
		print(f"Loading replay with: {len(replay_data.get('moves', []))} moves")
		print(f"White: {replay_data.get('white', '?')}, Black: {replay_data.get('black', '?')}")
		print(f"Replay file info: {replay_data.get('event', 'Unknown')}, Date: {replay_data.get('date', 'Unknown')}")
		
		# Extract moves from the replay data and ensure it's a list
		self.moves = replay_data.get("moves", [])
		if not isinstance(self.moves, list):
			print(f"Warning: 'moves' is not a list. Type: {type(self.moves)}. Converting to empty list.")
			self.moves = []
		
		print(f"Loaded {len(self.moves)} moves: {self.moves[:min(5, len(self.moves))]}")
		self.index = 0
		self.board = ChessBoard()
		
		# Set display message using data from the actual replay
		self.status_message = f"Replay: {replay_data.get('white','?')} vs {replay_data.get('black','?')}"
		
		# Initialize playback state
		self.playing = False
		self.last_advance = 0.0
		if replay_data.get('auto_play', True):
			self.playing = True
		# Layout similar to ChessGUI for board/panel reuse
		self.square_size = SQUARE_SIZE
		self.board_px = BOARD_SIZE_PX
		self.board_left = 0
		self.board_top = 0
		self.panel_left = self.board_px
		self.panel_rect = pygame.Rect(self.panel_left, 0, self.screen.get_width() - self.panel_left, self.screen.get_height())
		
		# Control buttons
		self.buttons = []
		self.control_height = 50  # Height of the controls area
		self._recompute_layout()
		# Back button state
		self.back_button_rect = pygame.Rect(0,0,0,0)
		self.exit_mode = 'done'  # 'back', 'quit', 'done'

	def _recompute_layout(self):
		w, h = self.screen.get_size()
		min_panel = 260
		max_board_w = max(0, w - min_panel)
		board_px = min(h, max_board_w)
		min_square = 48
		min_board = min_square * 8
		if board_px < min_board:
			board_px = min_board if w >= min_board + min_panel else max(8 * 32, max_board_w)
		square_size = max(16, board_px // 8)
		board_px = square_size * 8
		panel_left = board_px
		panel_width = max(140, w - panel_left)
		self.square_size = square_size
		self.board_px = board_px
		self.board_left = 0
		self.board_top = 0 if h <= board_px else (h - board_px) // 2
		self.panel_left = panel_left
		self.panel_rect = pygame.Rect(self.panel_left, 0, panel_width, h)
		
		# Calculate control button positions with enhanced layout matching the second image
		panel_usable_width = panel_width - 40  # 20px padding on each side
		
		# Make the play/pause button slightly larger than the navigation buttons
		nav_button_size = min(48, max(38, panel_usable_width // 5))
		play_button_size = min(54, max(44, panel_usable_width // 4))
		
		# Calculate spacing between buttons based on available width
		# Wider spacing between buttons for a more elegant look
		button_spacing = min(20, max(10, panel_usable_width // 10))
		
		# Calculate total width needed for all buttons
		total_button_width = (2 * nav_button_size) + play_button_size + (2 * button_spacing)
		
		# Calculate starting position to center the button group within the panel
		start_x = self.panel_left + (panel_width - total_button_width) // 2
		
		# Default controls_y will be set in _draw_replay based on content
		self.controls_y = 180  # This is just a placeholder, will be adjusted during drawing
		
		# Define button positions with improved arrangement
		self.buttons = []
		
		# Previous button
		prev_rect = pygame.Rect(start_x, self.controls_y, nav_button_size, nav_button_size)
		self.buttons.append(('prev', prev_rect))
		
		# Play/Pause button (larger and centered)
		play_rect = pygame.Rect(
			start_x + nav_button_size + button_spacing, 
			self.controls_y - (play_button_size - nav_button_size) // 2,  # Center vertically
			play_button_size, 
			play_button_size
		)
		self.buttons.append(('play', play_rect))
		
		# Next button
		next_rect = pygame.Rect(
			start_x + nav_button_size + button_spacing + play_button_size + button_spacing, 
			self.controls_y, 
			nav_button_size, 
			nav_button_size
		)
		self.buttons.append(('next', next_rect))

	def run(self) -> str:
		running = True
		while running:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
					self.exit_mode = 'quit'
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_RIGHT:
						self.step_forward()
					elif event.key == pygame.K_LEFT:
						self.step_back()
					elif event.key == pygame.K_SPACE:
						self.playing = not self.playing
					elif event.key == pygame.K_ESCAPE:
						self.exit_mode = 'back'
						running = False
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					mx, my = event.pos
					# Back button click
					if self.back_button_rect.collidepoint(mx, my):
						self.exit_mode = 'back'
						running = False
					else:
						for action, rect in self.buttons:
							if rect.collidepoint(mx, my):
								if action == 'prev':
									self.step_back()
								elif action == 'play':
									self.playing = not self.playing
								elif action == 'next':
									self.step_forward()
								break
			if running and self.playing and time.time() - self.last_advance > 0.6:
				self.step_forward()
				self.last_advance = time.time()
			self._draw_replay()
			pygame.display.flip()
			self.clock.tick(FPS)
		# Do NOT quit pygame here to allow returning to browser
		return self.exit_mode

	def step_forward(self):
		if self.index < len(self.moves):
			try:
				# Get the move from the loaded moves list
				move_uci = self.moves[self.index]
				print(f"Processing move {self.index}: {move_uci}")
				
				# Create the chess.Move object from UCI string
				mv = chess.Move.from_uci(move_uci)
				
				# Check if this move is legal in the current position
				if mv in self.board.board.legal_moves:
					# Apply the move and advance the index
					self.board.board.push(mv)
					self.index += 1
					print(f"Move applied: {move_uci}, new position: {self.board.board.fen()}")
				else:
					# Handle illegal move
					print(f"ILLEGAL MOVE: {move_uci} at index {self.index}, FEN: {self.board.board.fen()}")
					print(f"Legal moves: {[m.uci() for m in self.board.board.legal_moves]}")
					
					# Skip this move 
					self.index += 1
					
					# If we reach the end of moves, stop auto-playing
					if self.index >= len(self.moves):
						self.playing = False
						
			except Exception as e:
				print(f"Error processing move at index {self.index}: {e}")
				# Skip the problematic move and continue
				self.index += 1
				# If we reach the end of moves, stop auto-playing
				if self.index >= len(self.moves):
					self.playing = False

	def step_back(self):
		if self.index > 0:
			self.board.board.pop()
			self.index -= 1
			
	def _draw_playback_controls(self):
		try:
			# Draw control panel background with dark, sleek style
			controls_rect = pygame.Rect(
				self.panel_left + 15,
				self.controls_y - 5,
				self.panel_rect.width - 30,
				80  # Increased height for better spacing
			)
			# Themed background for controls section
			pygame.draw.rect(self.screen, COLOR_PANEL_BG, controls_rect, border_radius=8)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, controls_rect, 1, border_radius=8)
			
			# Calculate button layout to center them properly
			button_area_width = sum(rect.width for _, rect in self.buttons) + 20  # 10px spacing between buttons
			start_x = self.panel_left + (self.panel_rect.width - button_area_width) // 2
			
			# Draw each control button
			x_offset = 0
			for action, rect in self.buttons:
				# Update button position for perfect centering
				rect.x = start_x + x_offset
				rect.y = self.controls_y + 10  # Better vertical centering
				
				# Draw button background with improved style
				if action == 'play':
					color = (60, 130, 60) if self.playing else (50, 50, 65)
				else:
					color = (50, 50, 65)  # darker color for prev/next
				
				# Button with circular design
				pygame.draw.circle(self.screen, color, rect.center, rect.width // 2)
				pygame.draw.circle(self.screen, COLOR_BUTTON_BORDER, rect.center, rect.width // 2, 2)
				
				# Draw button icons with improved visibility
				if action == 'prev':
					# Previous triangle
					icon_size = rect.width // 2
					points = [
						(rect.centerx + icon_size // 2, rect.centery - icon_size // 2),
						(rect.centerx + icon_size // 2, rect.centery + icon_size // 2),
						(rect.centerx - icon_size // 2, rect.centery),
					]
					pygame.draw.polygon(self.screen, (240, 240, 245), points)
				elif action == 'play':
					if self.playing:
						# Pause icon (two vertical bars)
						bar_w = rect.width // 6
						pygame.draw.rect(self.screen, (240, 240, 245), 
									   (rect.centerx - bar_w - 3, rect.centery - rect.height // 4, 
										bar_w, rect.height // 2))
						pygame.draw.rect(self.screen, (240, 240, 245), 
									   (rect.centerx + 3, rect.centery - rect.height // 4, 
										bar_w, rect.height // 2))
					else:
						# Play triangle
						icon_size = rect.width // 2
						points = [
							(rect.centerx - icon_size // 3, rect.centery - icon_size // 2),
							(rect.centerx - icon_size // 3, rect.centery + icon_size // 2),
							(rect.centerx + icon_size // 2, rect.centery),
						]
						pygame.draw.polygon(self.screen, (240, 240, 245), points)
				elif action == 'next':
					# Next triangle
					icon_size = rect.width // 2
					points = [
						(rect.centerx - icon_size // 2, rect.centery - icon_size // 2),
						(rect.centerx - icon_size // 2, rect.centery + icon_size // 2),
						(rect.centerx + icon_size // 2, rect.centery),
					]
					pygame.draw.polygon(self.screen, (240, 240, 245), points)
				
				# Move to next button position
				x_offset += rect.width + 10
					
			# Show current playback state on the right side of the controls
			small = get_mono_font(14)
			status_text = "Playing" if self.playing else "Paused"
			status_color = (130, 200, 130) if self.playing else (180, 180, 180)
			status = small.render(status_text, True, status_color)
			
			# Position the status text on the right side of the controls panel
			next_button = next((rect for action, rect in self.buttons if action == 'next'), None)
			if next_button:
				# Calculate position to the right of the next button
				status_x = next_button.right + 20
				status_y = next_button.centery
				status_rect = status.get_rect(midleft=(status_x, status_y))
			else:
				# Fallback position if next button isn't found
				status_rect = status.get_rect(midright=(controls_rect.right - 15, controls_rect.centery))
				
			self.screen.blit(status, status_rect)
			
		except Exception as e:
			# Silently fail if there's an error drawing controls
			print(f"Error drawing playback controls: {e}")

	def _draw_replay(self):
		# reuse drawing from ChessGUI minimal pieces
		gui_stub = ChessGUI.__new__(ChessGUI)
		gui_stub.screen = self.screen
		gui_stub.board = self.board
		gui_stub.last_move = self.board.board.move_stack[-1] if self.board.board.move_stack else None
		gui_stub.selected_square = None
		gui_stub.legal_destinations = []
		# Layout attributes for drawing methods
		gui_stub.square_size = self.square_size
		gui_stub.board_px = self.board_px
		gui_stub.board_left = self.board_left
		gui_stub.board_top = self.board_top
		gui_stub.panel_left = self.panel_left
		gui_stub.panel_rect = self.panel_rect
		ChessGUI._draw_board(gui_stub)
		
		# Panel with sleeker design - gradient effect
		pygame.draw.rect(self.screen, COLOR_PANEL_BG, self.panel_rect)
		
		# Add subtle gradient highlight at the top
		gradient_height = 80
		for i in range(gradient_height):
			# Calculate a brightness factor that decreases with distance from top
			brightness = 15 - int(15 * (i / gradient_height))
			if brightness <= 0:
				continue
				
			# Create a slightly lighter color for the gradient line
			gradient_color = (
				min(255, COLOR_PANEL_BG[0] + brightness),
				min(255, COLOR_PANEL_BG[1] + brightness),
				min(255, COLOR_PANEL_BG[2] + brightness)
			)
			
			pygame.draw.line(
				self.screen,
				gradient_color,
				(self.panel_left, i),
				(self.panel_rect.right, i),
				1
			)
		font = get_font(28)  # Larger, more prominent title
		small = get_mono_font(16)
		
		# Draw main title with better styling
		title_y = 20
		title_text = font.render("Replay", True, COLOR_TEXT)
		self.screen.blit(title_text, (self.panel_left + 20, title_y))
		# Back button (top-right of panel)
		btn_w, btn_h = 80, 30
		bx = self.panel_rect.right - btn_w - 20
		by = title_y
		self.back_button_rect = pygame.Rect(bx, by, btn_w, btn_h)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BG, self.back_button_rect, border_radius=6)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, self.back_button_rect, 2, border_radius=6)
		back_font = get_mono_font(16)
		back_txt = back_font.render("Back", True, COLOR_TEXT)
		self.screen.blit(back_txt, back_txt.get_rect(center=self.back_button_rect.center))
		
		# Draw subtle underline beneath the title
		title_width = title_text.get_width()
		pygame.draw.line(
			self.screen,
			(80, 80, 90),
			(self.panel_left + 20, title_y + title_text.get_height() + 5),
			(self.panel_left + 20 + title_width, title_y + title_text.get_height() + 5),
			2
		)
		
		# Draw game information with cleaner spacing and file-specific data
		info_y = title_y + 50  # More space after title
		
		# Generate display information directly from the current replay data
		white_player = self.replay_data.get('white', '?')
		black_player = self.replay_data.get('black', '?')
		result = self.replay_data.get('result', '*')
		event = self.replay_data.get('event', 'Unknown Game')
		
		info_lines = [
			f"Replay: {white_player} vs {black_player}",
			f"Event: {event}",
			f"Result: {result}",
			f"Move {self.index}/{len(self.moves)}"
		]
		
		for l in info_lines:
			txt = small.render(l, True, COLOR_TEXT)
			self.screen.blit(txt, (self.panel_left + 20, info_y))
			info_y += txt.get_height() + 8  # Better line spacing
		
		# Add a subtle separator line
		separator_y = info_y + 20
		pygame.draw.line(
			self.screen, 
			(50, 50, 60), 
			(self.panel_left + 20, separator_y), 
			(self.panel_rect.right - 20, separator_y), 
			1
		)
		
		# Update controls position - remove explicit "Playback Controls" title
		# since it's visually implied by the separator and layout
		self.controls_y = separator_y + 25
		
		# Draw playback control buttons
		self._draw_playback_controls()
		
		# Draw keyboard control help text with better spacing and styling
		help_y = self.controls_y + 95  # More space after controls + status text
		
		# Draw subtle background for help text
		help_bg_rect = pygame.Rect(
			self.panel_left + 15, 
			help_y - 5,
			self.panel_rect.width - 30,
			50
		)
		pygame.draw.rect(self.screen, COLOR_PANEL_BG, help_bg_rect, border_radius=5)
		
		# Draw help text
		help_text = small.render("Keys: Left/Right step, Space play/pause", True, COLOR_TEXT_FAINT)
		self.screen.blit(help_text, (self.panel_left + 20, help_y))
		help_y += help_text.get_height() + 6
		help_text2 = small.render("Close window to exit", True, COLOR_TEXT_FAINT)
		self.screen.blit(help_text2, (self.panel_left + 20, help_y))


# Helper utilities
def RIGHT_BUTTON_WIDTH() -> int:
	return 180

def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
	words = text.split()
	lines: List[str] = []
	cur = ''
	for w in words:
		test = f"{cur} {w}".strip()
		if font.size(test)[0] <= max_width:
			cur = test
		else:
			if cur:
				lines.append(cur)
			cur = w
	if cur:
		lines.append(cur)
	return lines

__all__ = ["ChessGUI", "ReplayViewer"]


# ------------------- Start Screen & App Controller -------------------
class StartScreen:
	def __init__(self, screen):
		self.screen = screen
		self.selection = None  # 'human', 'random', 'replay'
		self.running = True
		self.buttons = []
		self._recompute_layout()

	def _recompute_layout(self):
		# Calculate button positions based on current screen size
		self.width, self.height = self.screen.get_size()
		self.btn_width = min(360, self.width - 80)
		self.title_y = max(80, self.height // 6)
		self.btn_start_y = self.title_y + 100
		self.btn_spacing = min(90, (self.height - self.btn_start_y - 80) // 4)

	def run(self) -> str:
		clock = pygame.time.Clock()
		while self.running and self.selection is None:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.running = False
				if event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					mx, my = event.pos
					for name, rect in self.buttons:
						if rect.collidepoint(mx, my):
							self.selection = name
							break
			self._draw()
			pygame.display.flip()
			clock.tick(30)
		return self.selection or "quit"

	def _draw(self):
		self.screen.fill(BACKGROUND_COLOR)
		try:
			# Scale fonts based on screen size
			title_size = max(36, min(48, self.width // 20))
			btn_size = max(22, min(28, self.width // 30))
			small_size = max(12, min(14, self.width // 70))
			
			title_font = get_font(title_size)
			btn_font = get_font(btn_size)
			small = get_mono_font(small_size)
		except Exception:
			return
			
		title = title_font.render("Chess Engine", True, COLOR_TEXT)
		self.screen.blit(title, title.get_rect(center=(self.width//2, self.title_y)))
		
		options = [
			("human", "Human vs AI"),
			("random", "AI vs AI"),
			("replay", "Replays")
		]
		self.buttons.clear()
		y = self.btn_start_y
		
		for key, label in options:
			rect = pygame.Rect(self.width//2 - self.btn_width//2, y, self.btn_width, 60)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BG, rect, border_radius=8)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 3, border_radius=8)
			txt = btn_font.render(label, True, COLOR_TEXT)
			self.screen.blit(txt, txt.get_rect(center=rect.center))
			self.buttons.append((key, rect))
			y += self.btn_spacing
			
		h1 = small.render("Esc / Close window to quit", True, COLOR_TEXT_FAINT)
		self.screen.blit(h1, (self.width//2 - h1.get_width()//2, self.height-60))


class AgentSelectScreen:
	"""Second-step screen shown after choosing Human vs AI to pick the AI agent type."""
	def __init__(self, screen):
		self.screen = screen
		self.selection: Optional[str] = None  # 'alphabeta','random','back'
		self.running = True
		self.buttons: list[tuple[str, pygame.Rect]] = []
		self._recompute_layout()

	def _recompute_layout(self):
		self.width, self.height = self.screen.get_size()
		self.btn_width = min(400, self.width - 80)
		self.title_y = max(70, self.height // 6)
		self.btn_start_y = self.title_y + 110
		self.btn_spacing = min(90, (self.height - self.btn_start_y - 120) // 4)

	def run(self) -> str:
		clock = pygame.time.Clock()
		while self.running and self.selection is None:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.selection = 'quit'
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					self.selection = 'back'
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					mx, my = event.pos
					for name, rect in self.buttons:
						if rect.collidepoint(mx, my):
							self.selection = name
							break
			self._draw()
			pygame.display.flip()
			clock.tick(30)
		return self.selection or 'back'

	def _draw(self):
		self.screen.fill(BACKGROUND_COLOR)
		try:
			title_font = get_font(max(34, min(46, self.width // 18)))
			btn_font = get_font(max(22, min(28, self.width // 32)))
			small = get_mono_font(max(12, min(14, self.width // 70)))
		except Exception:
			return

		title = title_font.render("Select AI Opponent", True, COLOR_TEXT)
		self.screen.blit(title, title.get_rect(center=(self.width//2, self.title_y)))

		options = [
			('alphabeta', 'Alpha-Beta Engine'),
			('random', 'Random Agent'),
			('back', 'Back')
		]
		self.buttons.clear()
		y = self.btn_start_y
		for key, label in options:
			rect = pygame.Rect(self.width//2 - self.btn_width//2, y, self.btn_width, 60)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BG, rect, border_radius=8)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 3, border_radius=8)
			txt = btn_font.render(label, True, COLOR_TEXT)
			self.screen.blit(txt, txt.get_rect(center=rect.center))
			self.buttons.append((key, rect))
			y += self.btn_spacing

		h1 = small.render("Esc / Back to main menu", True, COLOR_TEXT_FAINT)
		self.screen.blit(h1, (self.width//2 - h1.get_width()//2, self.height - 60))


class AlphaBetaConfig:
	def __init__(self, depth: int = 3, eval_key: str = 'mat_mob', ordering: bool = True):
		self.depth = depth
		self.eval_key = eval_key
		self.ordering = ordering


class ConfigScreen:
	"""Generic screen to configure one AlphaBeta agent.

	Allows changing depth, evaluation function, and move ordering.
	Return value is AlphaBetaConfig or 'back'/'quit'.
	"""
	def __init__(self, screen, title: str = "Configure Alpha-Beta"):
		self.screen = screen
		self.title = title
		self.running = True
		self.result: Optional[AlphaBetaConfig] = None
		self.depth = 3
		self.eval_idx = 0
		self.eval_keys = ['material', 'mat_mob', 'aggressive']
		self.ordering = True
		self.buttons: list[tuple[str, pygame.Rect]] = []
		self._recompute_layout()

	def _recompute_layout(self):
		self.width, self.height = self.screen.get_size()
		self.btn_width = min(420, self.width - 100)
		self.title_y = 70
		self.btn_start_y = self.title_y + 80
		self.btn_spacing = 72

	def run(self):
		clock = pygame.time.Clock()
		while self.running and self.result is None:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					return 'quit'
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					return 'back'
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					mx, my = event.pos
					for name, rect in self.buttons:
						if rect.collidepoint(mx, my):
							if name == 'depth-':
								self.depth = max(1, self.depth - 1)
							elif name == 'depth+':
								self.depth = min(12, self.depth + 1)
							elif name == 'eval':
								self.eval_idx = (self.eval_idx + 1) % len(self.eval_keys)
							elif name == 'ordering':
								self.ordering = not self.ordering
							elif name == 'apply':
								self.result = AlphaBetaConfig(self.depth, self.eval_keys[self.eval_idx], self.ordering)
							elif name == 'back':
								return 'back'
			self._draw()
			pygame.display.flip()
			clock.tick(30)
		return self.result

	def _draw(self):
		self.screen.fill(BACKGROUND_COLOR)
		try:
			title_font = get_font(40)
			btn_font = get_font(24)
			small = get_mono_font(14)
		except Exception:
			return
		title = title_font.render(self.title, True, COLOR_TEXT)
		self.screen.blit(title, title.get_rect(center=(self.width//2, self.title_y)))
		self.buttons.clear()
		# Depth controls
		center_x = self.width // 2
		row_y = self.btn_start_y
		def add_button(key, label, w=140, h=50, x=None, y=None):
			if x is None: x = center_x - w//2
			if y is None: y = row_y
			rect = pygame.Rect(x, y, w, h)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BG, rect, border_radius=8)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 3, border_radius=8)
			lab = btn_font.render(label, True, COLOR_TEXT)
			self.screen.blit(lab, lab.get_rect(center=rect.center))
			self.buttons.append((key, rect))
			return rect
		# Depth row
		minus_r = add_button('depth-', '- D', w=90, x=center_x - 220)
		value_r = add_button('depthv', f'Depth: {self.depth}', w=180, x=center_x - 90)
		plus_r = add_button('depth+', '+ D', w=90, x=center_x + 100)
		# Eval row
		row_y += self.btn_spacing
		add_button('eval', f'Eval: {self.eval_keys[self.eval_idx]}', w=360, x=center_x - 180)
		# Ordering row
		row_y += self.btn_spacing
		ord_label = 'Ordering: ON' if self.ordering else 'Ordering: OFF'
		add_button('ordering', ord_label, w=260, x=center_x - 130)
		# Apply / Back
		row_y += self.btn_spacing
		add_button('apply', 'Apply', w=160, x=center_x - 180)
		add_button('back', 'Back', w=160, x=center_x + 20)
		h1 = small.render('Click Eval to cycle options. Depth limits 1-12.', True, COLOR_TEXT_FAINT)
		self.screen.blit(h1, (center_x - h1.get_width()//2, self.height - 70))
		h2 = small.render('Apply to confirm or Back to cancel.', True, COLOR_TEXT_FAINT)
		self.screen.blit(h2, (center_x - h2.get_width()//2, self.height - 50))


class AIVsAISelectScreen:
	"""Screen for choosing AI vs AI matchup variant."""
	def __init__(self, screen):
		self.screen = screen
		self.selection: Optional[str] = None  # 'random','alphabeta','mixed','back'
		self.running = True
		self.buttons: list[tuple[str, pygame.Rect]] = []
		self._recompute_layout()

	def _recompute_layout(self):
		self.width, self.height = self.screen.get_size()
		self.btn_width = min(420, self.width - 80)
		self.title_y = max(70, self.height // 6)
		self.btn_start_y = self.title_y + 110
		self.btn_spacing = min(90, (self.height - self.btn_start_y - 120) // 4)

	def run(self) -> str:
		clock = pygame.time.Clock()
		while self.running and self.selection is None:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.selection = 'quit'
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					self.selection = 'back'
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					mx, my = event.pos
					for name, rect in self.buttons:
						if rect.collidepoint(mx, my):
							self.selection = name
							break
			self._draw()
			pygame.display.flip()
			clock.tick(30)
		return self.selection or 'back'

	def _draw(self):
		self.screen.fill(BACKGROUND_COLOR)
		try:
			title_font = get_font(max(34, min(46, self.width // 18)))
			btn_font = get_font(max(22, min(28, self.width // 32)))
			small = get_mono_font(max(12, min(14, self.width // 70)))
		except Exception:
			return

		title = title_font.render("Select AI vs AI Matchup", True, COLOR_TEXT)
		self.screen.blit(title, title.get_rect(center=(self.width//2, self.title_y)))

		options = [
			('alphabeta', 'Alpha-Beta vs Alpha-Beta'),
			('random', 'Random vs Random'),
			('mixed', 'Random (White) vs Alpha-Beta (Black)'),
			('back', 'Back')
		]
		self.buttons.clear()
		y = self.btn_start_y
		for key, label in options:
			# Determine lines (multi-line for long mixed label to show sides clearly)
			if key == 'mixed':
				lines = ['Random (White)', 'Alpha-Beta (Black)']
			else:
				lines = [label]
			# Adaptive font sizing so longest line fits
			_render_font = btn_font
			max_width_allowed = self.btn_width - 40
			while True:
				longest = max(_render_font.size(l)[0] for l in lines)
				if longest <= max_width_allowed or _render_font.get_height() <= 14:
					break
				try:
					_render_font = get_font(_render_font.get_height() - 2)
				except Exception:
					break
			line_height = _render_font.get_height()
			padding_v = 12
			inner_spacing = 4
			needed_h = padding_v * 2 + line_height * len(lines) + inner_spacing * (len(lines)-1)
			rect = pygame.Rect(self.width//2 - self.btn_width//2, y, self.btn_width, needed_h)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BG, rect, border_radius=8)
			pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, rect, 3, border_radius=8)
			cy = rect.y + padding_v
			for l in lines:
				txt = _render_font.render(l, True, COLOR_TEXT)
				self.screen.blit(txt, txt.get_rect(center=(rect.centerx, cy + line_height//2)))
				cy += line_height + inner_spacing
			self.buttons.append((key, rect))
			y += needed_h +  (self.btn_spacing - 60)  # adjust spacing relative to original 60px buttons

		h1 = small.render("Esc / Back to main menu", True, COLOR_TEXT_FAINT)
		self.screen.blit(h1, (self.width//2 - h1.get_width()//2, self.height - 60))


class ReplayBrowser:
	def __init__(self, screen):
		self.screen = screen
		self.running = True
		self.selected_file: Optional[str] = None
		self.scroll = 0
		self.files: List[str] = self._load_files()
		# Cache loaded metadata to avoid re-reading JSON every frame
		self._metadata_cache: dict[str, dict] = {}
		self.back_button_rect = pygame.Rect(0,0,0,0)
		self._recompute_layout()

	def _recompute_layout(self):
		self.width, self.height = self.screen.get_size()
		# Make list responsive: occupy up to 90% width with 20px margins, min 400px.
		available = max(0, self.width - 40)  # 20px margin each side
		desired = int(self.width * 0.9)
		self.list_width = max(400, min(desired, available))
		self.item_height = 40
		self.title_y = 20
		self.list_start_y = self.title_y + 50
		self.list_visible_height = self.height - self.list_start_y - 40
		self.max_scroll = max(0, len(self.files) * self.item_height - self.list_visible_height)

	def _load_files(self) -> List[str]:
		os.makedirs('replays', exist_ok=True)
		# Single recursive search (already includes top-level); previous implementation
		# performed two overlapping globs which produced duplicate paths.
		files = glob.glob(os.path.join('replays', '**', '*.json'), recursive=True)
		# Deduplicate while preserving order (in case OS/glob returns duplicates)
		seen = set()
		unique_files: List[str] = []
		for f in files:
			if f not in seen:
				seen.add(f)
				unique_files.append(f)
		# Validate each file to ensure it's a valid JSON (lightweight check)
		valid_files: List[str] = []
		for f in unique_files:
			try:
				with open(f, 'r') as file:
					file.read(10)
				valid_files.append(f)
			except Exception as e:
				print(f"Skipping invalid replay file {f}: {e}")
		# Sort newest first
		valid_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
		return valid_files

	def run(self) -> Optional[str]:
		clock = pygame.time.Clock()
		while self.running and self.selected_file is None:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.running = False
				elif event.type == pygame.VIDEORESIZE:
					self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
					self._recompute_layout()
				elif event.type == pygame.MOUSEBUTTONDOWN:
					if event.button == 1:
						# Back button click
						mx, my = event.pos
						if self.back_button_rect.collidepoint(mx, my):
							self.running = False
							continue
						mx, my = event.pos
						self._handle_click(mx, my)
					elif event.button == 4:  # Scroll up
						self.scroll = max(0, self.scroll - self.item_height)
					elif event.button == 5:  # Scroll down
						self.scroll = min(self.max_scroll, self.scroll + self.item_height)
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						self.running = False
			self._draw()
			pygame.display.flip()
			clock.tick(30)
		return self.selected_file

	def _handle_click(self, mx, my):
		# Check if click is within list area
		if 20 <= mx <= 20 + self.list_width and self.list_start_y <= my <= self.list_start_y + self.list_visible_height:
			idx = (my - self.list_start_y + self.scroll) // self.item_height
			if 0 <= idx < len(self.files):
				self.selected_file = self.files[idx]

	def _draw(self):
		self.screen.fill(BACKGROUND_COLOR)
		try:
			# Scale fonts based on screen size
			title_size = max(32, min(40, self.width // 25))
			item_size = max(16, min(18, self.width // 50))
			small_size = max(12, min(14, self.width // 70))
			
			title_font = get_font(title_size)
			item_font = get_mono_font(item_size)
			small = get_mono_font(small_size)
		except Exception:
			return
			
		# Title and Back button (mouse alternative to Esc)
		title = title_font.render("Replays", True, COLOR_TEXT)
		self.screen.blit(title, (30, self.title_y))
		btn_w, btn_h = 90, 36
		bx = 30 + max(self.list_width, 600) - btn_w  # align with list width
		by = self.title_y - 4
		self.back_button_rect = pygame.Rect(bx, by, btn_w, btn_h)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BG, self.back_button_rect, border_radius=8)
		pygame.draw.rect(self.screen, COLOR_BUTTON_BORDER, self.back_button_rect, 2, border_radius=8)
		bb_font = get_mono_font(max(14, min(18, self.width // 70)))
		bb_txt = bb_font.render("Back", True, COLOR_TEXT)
		self.screen.blit(bb_txt, bb_txt.get_rect(center=self.back_button_rect.center))
		
		# Draw list items
		y = self.list_start_y - self.scroll
		if not self.files:
			self.screen.blit(item_font.render("No replays yet", True, COLOR_TEXT_FAINT), (40, y))
		
		# Only draw visible items
		visible_start = self.scroll // self.item_height
		visible_end = visible_start + (self.list_visible_height // self.item_height) + 2
		visible_files = self.files[visible_start:min(visible_end, len(self.files))]
		
		for i, f in enumerate(visible_files):
			item_y = y + (i * self.item_height)
			if item_y < self.list_start_y - self.item_height or item_y > self.list_start_y + self.list_visible_height:
				continue  # Skip if out of view
				
			base = os.path.basename(f)
			
			# Try to load game metadata for better display
			if f in self._metadata_cache:
				game_data = self._metadata_cache[f]
			else:
				try:
					game_data = GameIO.load_replay(f)
				except Exception:
					game_data = None
				self._metadata_cache[f] = game_data  # Cache even None to avoid repeated attempts
			try:
				if game_data:
					white = game_data.get('white', '?')
					black = game_data.get('black', '?')
					result = game_data.get('result', '?')
					mode = game_data.get('mode', '')
					date_str = ""
					if 'date' in game_data:
						date = game_data['date']
						if len(date) >= 15:
							date_str = f"{date[6:8]}/{date[4:6]}/{date[0:4]} {date[9:11]}:{date[11:13]}"
						else:
							date_str = date
					else:
						if len(base) > 15 and base[8] == '_':
							date_str = f"{base[6:8]}/{base[4:6]}/{base[0:4]} {base[9:11]}:{base[11:13]}"
						else:
							m = re.search(r'gui_(\d+)', base)
							if m:
								ts = int(m.group(1))
								date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(ts))
					if mode:
						display_name = f"{date_str} - {mode} - {result}"
					else:
						display_name = f"{date_str} - {white} vs {black} - {result}"
				else:
					display_name = base
			except Exception:
				display_name = base
			
			# Truncate if still too long
			max_chars = max(35, self.list_width // item_size // 2)
			if len(display_name) > max_chars:
				display_name = display_name[:max_chars] + "..."
				
			rect = pygame.Rect(20, item_y, self.list_width, self.item_height - 6)
			pygame.draw.rect(self.screen, COLOR_PANEL_BG, rect, border_radius=6)
			txt = item_font.render(display_name, True, COLOR_TEXT)
			self.screen.blit(txt, (rect.x + 10, rect.y + 7))
		
		# Help text (mention Back button)
		hint = small.render("Scroll wheel to scroll, click file to play, Esc/Back to return", True, COLOR_TEXT_FAINT)
		self.screen.blit(hint, (20, self.height - 30))


class App:
	def __init__(self):
		if not pygame.get_init():
			pygame.init()
		# Load last window size if available
		self._settings_path = os.path.join('config', 'ui_settings.json')
		win_size = self._load_last_window_size() or WINDOW_SIZE
		self.screen = pygame.display.set_mode(win_size, pygame.RESIZABLE)
		pygame.display.set_caption("Chess AlphaBeta Engine")
		self._dirty_window_size = False  # track if size changed to avoid unnecessary writes

	def _load_last_window_size(self):
		try:
			if os.path.exists(self._settings_path):
				with open(self._settings_path, 'r') as f:
					data = json.load(f)
					w, h = data.get('window_width'), data.get('window_height')
					if isinstance(w, int) and isinstance(h, int) and 400 <= w <= 4000 and 300 <= h <= 3000:
						return (w, h)
		except Exception:
			pass
		return None

	def _save_last_window_size(self):
		try:
			os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
			w, h = self.screen.get_size()
			data = {"window_width": w, "window_height": h}
			with open(self._settings_path, 'w') as f:
				json.dump(data, f)
		except Exception as e:
			print(f"Warning: could not save window size: {e}")

	def run(self):
		while True:
			start = StartScreen(self.screen)
			choice = start.run()
			if choice == 'quit':
				self._save_last_window_size()
				break
			if choice == 'human':
				agent_screen = AgentSelectScreen(self.screen)
				agent = agent_screen.run()
				if agent in ('back', 'quit'):
					if agent == 'quit':
						self._save_last_window_size()
						break
					continue  # Return to main start screen
				depth = 3 if agent == 'alphabeta' else 1
				label = 'Human vs Alpha-Beta' if agent == 'alphabeta' else 'Human vs Random'
				ab_conf = None
				if agent == 'alphabeta':
					conf_screen = ConfigScreen(self.screen, title='Configure AI (Black)')
					res_conf = conf_screen.run()
					if res_conf in ('back','quit'):
						if res_conf == 'quit':
							self._save_last_window_size()
							break
						continue
					ab_conf = res_conf
				game = ChessGUI(ai=agent, depth=(ab_conf.depth if ab_conf else depth), human_plays_white=True, human_plays_black=False, label=label)
				# Store chosen eval/order for ChessGUI instantiation (extend constructor later if needed)
				if isinstance(game.ai_black, AlphaBetaAgent) and ab_conf:
					game.ai_black.depth = ab_conf.depth
					game.ai_black.eval_key = ab_conf.eval_key
					game.ai_black.eval_func = get_eval_function(ab_conf.eval_key)
					game.ai_black.use_move_ordering = ab_conf.ordering
				res = game.run()
				if res == 'quit':
					self._save_last_window_size()
					break
			elif choice == 'random':
				ai_select = AIVsAISelectScreen(self.screen)
				matchup = ai_select.run()
				if matchup in ('back','quit'):
					if matchup == 'quit':
						self._save_last_window_size()
						break
					continue
				if matchup == 'random':
					label = 'AI vs AI (Random)'
					game = ChessGUI(ai='random', depth=1, human_plays_white=False, human_plays_black=False, label=label)
				elif matchup == 'alphabeta':
					# Two config screens (white and black)
					conf_w = ConfigScreen(self.screen, title='Configure Alpha-Beta (White)')
					cw = conf_w.run()
					if cw in ('back','quit'):
						if cw == 'quit':
							self._save_last_window_size()
							break
						continue
					conf_b = ConfigScreen(self.screen, title='Configure Alpha-Beta (Black)')
					cb = conf_b.run()
					if cb in ('back','quit'):
						if cb == 'quit':
							self._save_last_window_size()
							break
						continue
					label = 'AI vs AI (Alpha-Beta vs Alpha-Beta)'
					game = ChessGUI(ai='alphabeta', depth=cb.depth, human_plays_white=False, human_plays_black=False, label=label)
					# configure both agents
					if isinstance(game.ai_white, AlphaBetaAgent):
						game.ai_white.depth = cw.depth
						game.ai_white.eval_key = cw.eval_key
						game.ai_white.eval_func = get_eval_function(cw.eval_key)
						game.ai_white.use_move_ordering = cw.ordering
					if isinstance(game.ai_black, AlphaBetaAgent):
						game.ai_black.depth = cb.depth
						game.ai_black.eval_key = cb.eval_key
						game.ai_black.eval_func = get_eval_function(cb.eval_key)
						game.ai_black.use_move_ordering = cb.ordering
				elif matchup == 'mixed':
					# Configure the alpha-beta (Black) only
					conf_b = ConfigScreen(self.screen, title='Configure Alpha-Beta (Black)')
					cb = conf_b.run()
					if cb in ('back','quit'):
						if cb == 'quit':
							self._save_last_window_size()
							break
						continue
					label = 'AI vs AI (Random White vs Alpha-Beta Black)'
					game = ChessGUI(ai='mixed_random_alphabeta', depth=cb.depth, human_plays_white=False, human_plays_black=False, label=label)
					if isinstance(game.ai_black, AlphaBetaAgent):
						game.ai_black.depth = cb.depth
						game.ai_black.eval_key = cb.eval_key
						game.ai_black.eval_func = get_eval_function(cb.eval_key)
						game.ai_black.use_move_ordering = cb.ordering
				else:
					continue
				res = game.run()
				if res == 'quit':
					self._save_last_window_size()
					break
			elif choice == 'replay':
				# Loop allowing multiple replays and back navigation
				while True:
					browser = ReplayBrowser(self.screen)
					file = browser.run()
					if not file or not os.path.exists(file):
						break  # Back to start screen
					from .game_ui import ReplayViewer  # circular safe
					from ..core.game_io import GameIO
					try:
						data = GameIO.load_replay(file)
						print(f"\nLoading replay file: {file}")
						print(f"File contents: {data}")
						if data and "moves" in data and len(data["moves"]) > 0:
							data['auto_play'] = True
							print(f"Starting replay with {len(data['moves'])} moves")
							print(f"First few moves: {data['moves'][:5]}")
							viewer = ReplayViewer(data)
							vres = viewer.run()
							if vres == 'back':
								continue  # choose another replay
							else:
								break  # quit or done
						else:
							print("Invalid replay data: missing moves or empty moves list")
							raise ValueError("Invalid replay data format")
					except Exception as e:
						print(f"Failed to load replay: {e}")
						pygame.draw.rect(self.screen, BACKGROUND_COLOR, pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height()))
						try:
							font = get_font(24)
							txt = font.render(f"Error loading replay file: {str(e)}", True, (255, 100, 100))
							self.screen.blit(txt, txt.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2)))
							pygame.display.flip()
							pygame.time.delay(2000)
						except Exception:
							pass
					finally:
						# After an attempt, loop either continues (back) or breaks (other exit)
						pass
					# If we reach here without continue, break to start screen
					break
			# After returning from a mode, loop back to start screen

