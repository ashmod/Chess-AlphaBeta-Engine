"""
Alpha-Beta pruned search implementation with transposition table.

Key features:
- configurable search depth
- alpha-beta pruning with transposition table for speed
- simple move ordering: captures first
- detection of terminal states and repetitions
- transposition table prevents infinite loops and speeds up search

"""
from __future__ import annotations
from typing import Any, Callable, List, Optional, Tuple, Dict
import math
import random
import chess

from .agent import Agent
from .evaluation import evaluate, get_eval_function


class TranspositionEntry:
    """Entry in the transposition table."""
    def __init__(self, value: float, depth: int, node_type: str = "exact"):
        self.value = value
        self.depth = depth
        self.node_type = node_type  # "exact", "lower", "upper"


class AlphaBetaAgent(Agent):
    def __init__(self, depth: int = 4, eval_key: str = "mat_mob", use_move_ordering: bool = True, name: str | None = None) -> None:
        self.depth = depth
        self.eval_key = eval_key
        self.eval_func = get_eval_function(eval_key)
        self.use_move_ordering = use_move_ordering
        self.transposition_table: Dict[int, TranspositionEntry] = {}
        super().__init__(name=name or f"AlphaBeta(d={depth},eval={eval_key},ord={'Y' if use_move_ordering else 'N'})")

    def select_move(self, board: Any) -> Any:
        """Return the best move found by alpha-beta search from `board`."""
        # Clear transposition table for each new search to prevent stale entries
        self.transposition_table.clear()
        
        best_score = -math.inf
        best_moves = []
        alpha = -math.inf
        beta = math.inf

        moves = list(_get_legal_moves(board))
        if self.use_move_ordering:
            moves = _order_moves(board, moves)
 
        chess_board = _get_chess_board(board)
        
        for move in moves:
            if isinstance(move, chess.Move):
                chess_board.push(move)
            else:
                chess_board.push_uci(str(move))
                
            score = -self._negamax(board, self.depth - 1, -beta, -alpha)
            chess_board.pop()

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif abs(score - best_score) < 0.01:  # Consider moves within small threshold as equal
                best_moves.append(move)
                
            if score > alpha:
                alpha = score

        if len(best_moves) > 1:
            captures = []
            for move in best_moves:
                if isinstance(move, chess.Move) and chess_board.is_capture(move):
                    captures.append(move)
            if captures:
                return random.choice(captures)
            return random.choice(best_moves)
        
        return best_moves[0] if best_moves else None

    def _negamax(self, board: Any, depth: int, alpha: float, beta: float) -> float:
        """Negamax variant of minimax with alpha-beta pruning and transposition table."""
        chess_board = _get_chess_board(board)
        
        position_hash = chess_board.fen().__hash__()
        
        if position_hash in self.transposition_table:
            entry = self.transposition_table[position_hash]
            if entry.depth >= depth:
                if entry.node_type == "exact":
                    return entry.value
                elif entry.node_type == "lower" and entry.value >= beta:
                    return entry.value
                elif entry.node_type == "upper" and entry.value <= alpha:
                    return entry.value
        
        # Terminal checks
        if _is_checkmate(board):
            return -99999.0
        if _is_stalemate(board):
            return 0.0
        if chess_board.is_repetition() or chess_board.is_fivefold_repetition():
            return 0.0  # Draw by repetition
        if chess_board.is_fifty_moves() or chess_board.is_seventyfive_moves():
            return 0.0  # Draw by move rule

        if depth <= 0:
            # Evaluation from White's perspective, convert to current player perspective
            ev = self.eval_func(board)
            result = ev if chess_board.turn == chess.WHITE else -ev
            # Store in transposition table
            self.transposition_table[position_hash] = TranspositionEntry(result, depth, "exact")
            return result

        original_alpha = alpha
        max_score = -math.inf
        moves = list(_get_legal_moves(board))
        if self.use_move_ordering:
            moves = _order_moves(board, moves)
        
        for move in moves:
            if isinstance(move, chess.Move):
                chess_board.push(move)
            else:
                chess_board.push_uci(str(move))
                
            val = -self._negamax(board, depth - 1, -beta, -alpha)
            chess_board.pop()

            max_score = max(max_score, val)
            alpha = max(alpha, val)
            if alpha >= beta:
                break  # Beta cutoff

        # Store result in transposition table
        if max_score <= original_alpha:
            node_type = "upper"
        elif max_score >= beta:
            node_type = "lower"
        else:
            node_type = "exact"
        
        self.transposition_table[position_hash] = TranspositionEntry(max_score, depth, node_type)
        
        return max_score if max_score != -math.inf else 0.0


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
    
    if hasattr(board, "board") and isinstance(board.board, chess.Board):
        return board.board.legal_moves
        
    raise AttributeError("Board object must provide a legal-move iterator.")

def _is_checkmate(board: Any) -> bool:
    """Check if the board is in checkmate."""
    if hasattr(board, "is_checkmate"):
        return board.is_checkmate()
        
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
    """Simple move ordering: prefer captures first, then others."""
    def _move_score(m):
        # Handle python-chess Move objects
        if isinstance(m, chess.Move):
            try:
                if hasattr(board, "board") and isinstance(board.board, chess.Board):
                    return 1000 if board.board.is_capture(m) else 0
                elif isinstance(board, chess.Board):
                    return 1000 if board.is_capture(m) else 0
            except Exception:
                pass
                
        # Check for other capture indicators
        if hasattr(m, "is_capture") and getattr(m, "is_capture"):
            return 1000
        if hasattr(m, "captured_piece") and getattr(m, "captured_piece") is not None:
            # Try to value capturing higher-value pieces
            cap = getattr(m, "captured_piece")
            sym = None
            if isinstance(cap, str):
                sym = cap
            else:
                sym = getattr(cap, "symbol", None) or getattr(cap, "kind", None)
                if callable(sym):
                    sym = sym()
            if sym:
                # Approximate value mapping
                sym = sym.upper()
                piece_value = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 100}.get(sym, 1)
                return 900 + piece_value
            return 900
        # Non-captures
        return 0

    try:
        return sorted(moves, key=_move_score, reverse=True)
    except Exception:
        return moves