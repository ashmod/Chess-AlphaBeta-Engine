"""
Heuristic evaluation functions for chess positions.

The evaluation returns a positive value when
the position favors White, negative when it favors Black.

"""
from typing import Any, Iterable, Tuple, Callable, Dict
import chess

# Simple material values
PIECE_VALUES = {
    "P": 1.0,  # pawn
    "N": 3.0,  # knight
    "B": 3.0,  # bishop
    "R": 5.0,  # rook
    "Q": 9.0,  # queen
    "K": 0.0,  # king (infinite value conceptually, but 0 here)
}


def _iter_pieces(board: Any) -> Iterable[Tuple[str, bool, Any]]:
    """Iterate over pieces on the board.
    """
    if isinstance(board, chess.Board):
        chess_board = board
    elif hasattr(board, "board") and isinstance(board.board, chess.Board):
        chess_board = board.board
    else:
        raise AttributeError(
            "Unable to iterate pieces on the board. Expected a python-chess Board or a wrapper with a .board attribute containing a chess.Board."
        )

    for sq in chess.SQUARES:
        piece = chess_board.piece_at(sq)
        if piece is None:
            continue
        # piece.symbol() returns 'P' for white pawn and 'p' for black pawn
        yield piece.symbol().upper(), bool(piece.color == chess.WHITE), sq


def material_score(board: Any) -> float:
    """Simple material-only evaluation: sum of piece values.

    Positive = advantage for White. Negative = advantage for Black.
    """
    total = 0.0
    for sym, is_white, _sq in _iter_pieces(board):
        val = PIECE_VALUES.get(sym.upper(), 0.0)
        total += val if is_white else -val
    return total


def mobility_score(board: Any) -> float:
    """Mobility: difference in number of legal moves (white - black), normalized.

    We use python-chess Board instances. For wrappers we accept objects
    with a `.board` attribute containing a chess.Board or a `.get_fen()` method
    that returns a FEN string.
    """
    def _to_chess_board(b: Any) -> chess.Board:
        if isinstance(b, chess.Board):
            return b
        if hasattr(b, "board") and isinstance(b.board, chess.Board):
            return b.board
        if hasattr(b, "get_fen"):
            try:
                return chess.Board(b.get_fen())
            except Exception:
                pass
        raise AttributeError("Unable to obtain a python-chess Board from the provided board object.")

    try:
        cb = _to_chess_board(board)
    except AttributeError:
        # Fallback
        if hasattr(board, "get_legal_moves"):
            lm = list(board.get_legal_moves())
            return len(lm) / 10.0
        if hasattr(board, "legal_moves"):
            lm = board.legal_moves
            return (len(list(lm)) if not isinstance(lm, list) else len(lm)) / 10.0
        return 0.0
    
    b_white = cb.copy()
    b_white.turn = chess.WHITE
    b_black = cb.copy()
    b_black.turn = chess.BLACK

    moves_white = len(list(b_white.legal_moves))
    moves_black = len(list(b_black.legal_moves))

    total = moves_white + moves_black
    if total == 0:
        return 0.0
    # Return a normalized difference in (-1, 1): positive means White has more mobility
    return (moves_white - moves_black) / float(total)


def evaluate_material(board: Any) -> float:
    """Material only (baseline)."""
    return material_score(board)


def evaluate_material_mobility(board: Any) -> float:
    """Material + small mobility bonus (legacy default)."""
    mat = material_score(board)
    mob = mobility_score(board)
    return mat * 1.0 + mob * 0.1


def evaluate_aggressive(board: Any) -> float:
    """Material + higher mobility weight + central occupation bonus.

    Central occupation encourages quick development / center control.
    """
    mat = material_score(board)
    mob = mobility_score(board)
    center_bonus = 0.0
    try:
        if hasattr(board, "board") and isinstance(board.board, chess.Board):
            cb = board.board
            centers = [chess.D4, chess.E4, chess.D5, chess.E5]
            for sq in centers:
                p = cb.piece_at(sq)
                if p:
                    center_bonus += 0.15 if p.color == chess.WHITE else -0.15
    except Exception:
        pass
    return mat * 1.0 + mob * 0.25 + center_bonus


# Backwards-compatible default evaluate symbol (material+mobility)
def evaluate(board: Any) -> float:  # type: ignore
    return evaluate_material_mobility(board)


EVAL_FUNCTIONS: Dict[str, Callable[[Any], float]] = {
    "material": evaluate_material,
    "mat_mob": evaluate_material_mobility,
    "aggressive": evaluate_aggressive,
}


def get_eval_function(key: str) -> Callable[[Any], float]:
    """Return evaluation function by key; fallback to default evaluate."""
    return EVAL_FUNCTIONS.get(key, evaluate)