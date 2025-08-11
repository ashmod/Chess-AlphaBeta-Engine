"""
Heuristic evaluation functions for chess positions.

The evaluation returns a positive value when
the position favors White, negative when it favors Black.

Because different board implementations name piece types differently,
this module tries to support a couple of common access patterns. If
core.Board exposes a specific method to get material/mapped pieces
(e.g., piece_map() in python-chess), adapt the helper `iter_pieces`.
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
    """Yield (piece_symbol, is_white, square) for every piece on board.

    Tries a few common APIs:
    - board.piece_map() -> {square: piece}
    - board.board (2D array of piece or None)
    - board.get_pieces() or board.pieces()

    The `piece_symbol` must be a one-letter code like 'P','N','B','R','Q','K'
    for the piece type (uppercase for white, lowercase or sign provided) —
    otherwise adapt this function for your core.Board representation.
    """
    # Check for python-chess ChessBoard
    if hasattr(board, "board") and isinstance(board.board, chess.Board):
        chess_board = board.board
        for sq in chess.SQUARES:
            piece = chess_board.piece_at(sq)
            if piece is not None:
                sym = piece.symbol()
                is_white = sym.isupper()
                yield sym.upper(), is_white, sq
        return
        
    # 1) python-chess-like: piece_map() -> {sq: Piece}
    if hasattr(board, "piece_map"):
        for sq, piece in board.piece_map().items():
            sym = getattr(piece, "symbol", None)
            if callable(sym):
                sym = sym()
            if sym is None:
                continue
            is_white = sym.isupper()
            yield sym.upper(), is_white, sq
        return

    # 2) board.board 2D array (rank-major) where each cell has (color, kind) or piece object
    if hasattr(board, "board"):
        bd = board.board
        # try to iterate squares
        for r, row in enumerate(bd):
            for c, cell in enumerate(row):
                if cell is None:
                    continue
                # try common shapes
                if isinstance(cell, str):
                    # e.g., 'P' or 'p'
                    is_white = cell.isupper()
                    yield cell.upper(), is_white, (r, c)
                else:
                    # try attributes
                    kind = getattr(cell, "kind", None) or getattr(cell, "symbol", None)
                    if callable(kind):
                        kind = kind()
                    if kind:
                        is_white = getattr(cell, "color", True)
                        yield kind.upper(), bool(is_white), (r, c)
        return

    # 3) generic get_pieces()/pieces()
    if hasattr(board, "get_pieces"):
        for piece in board.get_pieces():
            sym = getattr(piece, "symbol", None) or getattr(piece, "kind", None)
            if callable(sym):
                sym = sym()
            if not sym:
                continue
            is_white = getattr(piece, "color", True)
            yield sym.upper(), bool(is_white), getattr(piece, "square", None)
        return

    # 4) fallback: no pieces found
    raise AttributeError("Unable to iterate pieces on the board. Please adapt _iter_pieces to your Board API.")


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
    """Mobility: difference in number of legal moves (normalized).

    If board exposes generate_legal_moves() or legal_moves, we use them.
    """
    def count_moves_for(turn_value) -> int:
        # Check for python-chess board
        if hasattr(board, "board") and isinstance(board.board, chess.Board):
            return len(list(board.board.legal_moves))
            
        if hasattr(board, "generate_legal_moves"):
            return len(list(board.generate_legal_moves()))
        if hasattr(board, "legal_moves"):
            lm = board.legal_moves
            return len(list(lm)) if not isinstance(lm, list) else len(lm)
        if hasattr(board, "get_legal_moves"):
            return len(list(board.get_legal_moves()))
        # fallback
        return 0

    moves = count_moves_for(None)
    return moves / 10.0


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