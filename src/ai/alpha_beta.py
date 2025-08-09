"""
Alpha-Beta pruned search implementation.

Key features implemented:
- configurable search depth
- alpha-beta pruning
- simple move ordering: captures (if move.captured_piece exists) are searched first
- detection of terminal states using board.is_checkmate() and board.is_stalemate()

Notes on expected Board API (the methods used below):
- generate_legal_moves() -> iterable of Move objects
- push(move) and pop() -> mutate and rollback board state
- is_checkmate(), is_stalemate() -> booleans
- turn -> Truthy for White (or string 'white'/'black')

"""
from __future__ import annotations
from typing import Any, Callable, List, Optional, Tuple
import math
import chess

from .agent import Agent
from .evaluation import evaluate


class AlphaBetaAgent(Agent):
    def __init__(self, depth: int = 4, name: str | None = None) -> None:
        super().__init__(name=name or f"AlphaBeta(depth={depth})")
        self.depth = depth

    def select_move(self, board: Any) -> Any:
        """Return the best move found by alpha-beta search from `board`.

        The returned move is the move object (from board.generate_legal_moves())
        and should be acceptable by board.push(move).
        """
        best_score = -math.inf
        best_move = None
        alpha = -math.inf
        beta = math.inf

        moves = list(_get_legal_moves(board))
        # move ordering: try captures first if possible
        moves = _order_moves(board, moves)

        # Use the proper board object for push/pop operations
        chess_board = _get_chess_board(board)
        
        for move in moves:
            # Push the move
            if isinstance(move, chess.Move):
                chess_board.push(move)
            else:
                chess_board.push_uci(str(move))
                
            score = -self._negamax(board, self.depth - 1, -beta, -alpha)
            
            # Pop the move
            chess_board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score

        return best_move

    def _negamax(self, board: Any, depth: int, alpha: float, beta: float) -> float:
        """Negamax variant of minimax with alpha-beta pruning.

        Returns the evaluation from the perspective of the current player.
        """
        # Terminal checks
        if _is_checkmate(board):
            # if current side to move is checkmated -> very bad
            return -99999.0
        if _is_stalemate(board):
            return 0.0  # draw

        if depth <= 0:
            return evaluate(board)

        max_score = -math.inf
        moves = list(_get_legal_moves(board))
        moves = _order_moves(board, moves)

        # Use the proper board object for push/pop operations
        chess_board = _get_chess_board(board)
        
        for move in moves:
            # Push the move
            if isinstance(move, chess.Move):
                chess_board.push(move)
            else:
                chess_board.push_uci(str(move))
                
            val = -self._negamax(board, depth - 1, -beta, -alpha)
            
            # Pop the move
            chess_board.pop()

            if val > max_score:
                max_score = val
            if val > alpha:
                alpha = val
            if alpha >= beta:
                # pruning
                break
        return max_score if max_score != -math.inf else evaluate(board)


# -------------------- Helper functions --------------------

def _get_chess_board(board: Any) -> chess.Board:
    """Get the underlying chess.Board from a board object."""
    if isinstance(board, chess.Board):
        return board
    elif hasattr(board, "board") and isinstance(board.board, chess.Board):
        return board.board
    else:
        raise AttributeError("Board object does not have a valid chess.Board instance.")

def _get_legal_moves(board: Any):
    """Get legal moves from a board object."""
    if hasattr(board, "generate_legal_moves"):
        return board.generate_legal_moves()
    if hasattr(board, "legal_moves"):
        lm = board.legal_moves
        return lm if isinstance(lm, list) else list(lm)
    if hasattr(board, "get_legal_moves"):
        return board.get_legal_moves()
    
    # Try python-chess Board or ChessBoard class
    if hasattr(board, "board") and isinstance(board.board, chess.Board):
        return board.board.legal_moves
        
    raise AttributeError("Board object must provide a legal-move iterator.")


def _is_checkmate(board: Any) -> bool:
    """Check if the board is in checkmate."""
    if hasattr(board, "is_checkmate"):
        return board.is_checkmate()
        
    # Try python-chess Board or ChessBoard class
    if hasattr(board, "board") and isinstance(board.board, chess.Board):
        return board.board.is_checkmate()
        
    # fallback: no legal moves + in_check
    try:
        moves = list(_get_legal_moves(board))
        if len(moves) == 0 and hasattr(board, "is_in_check"):
            return board.is_in_check()
    except Exception:
        pass
    return False


def _is_stalemate(board: Any) -> bool:
    """Check if the board is in stalemate."""
    if hasattr(board, "is_stalemate"):
        return board.is_stalemate()
        
    # Try python-chess Board or ChessBoard class
    if hasattr(board, "board") and isinstance(board.board, chess.Board):
        return board.board.is_stalemate()
        
    try:
        moves = list(_get_legal_moves(board))
        if len(moves) == 0 and hasattr(board, "is_in_check"):
            return not board.is_in_check()
    except Exception:
        pass
    return False


def _order_moves(board: Any, moves: List[Any]) -> List[Any]:
    """Simple move ordering: prefer captures first, then others.

    Expects move objects to carry some information about capture, e.g.,
    move.captured_piece or move.is_capture or move.capture from core.Move type.
    If none exists, returns moves unmodified.
    """
    def _move_score(m):
        # Handle python-chess Move objects
        if isinstance(m, chess.Move):
            try:
                if hasattr(board, "board") and isinstance(board.board, chess.Board):
                    return 100 if board.board.is_capture(m) else 0
                elif isinstance(board, chess.Board):
                    return 100 if board.is_capture(m) else 0
            except Exception:
                pass
                
        # captures first
        if hasattr(m, "is_capture"):
            return 100 if getattr(m, "is_capture") else 0
        if hasattr(m, "captured_piece") and getattr(m, "captured_piece") is not None:
            # try to value capturing higher-value pieces
            cap = getattr(m, "captured_piece")
            # cap could be a symbol or object with 'symbol' or 'kind'
            sym = None
            if isinstance(cap, str):
                sym = cap
            else:
                sym = getattr(cap, "symbol", None) or getattr(cap, "kind", None)
                if callable(sym):
                    sym = sym()
            if sym:
                # approximate value mapping
                sym = sym.upper()
                return {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 100}.get(sym, 1)
            return 1
        # fallback
        return 0

    try:
        return sorted(moves, key=_move_score, reverse=True)
    except Exception:
        return moves