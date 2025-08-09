"""
Simple random agent that selects uniformly from legal moves.
"""
from typing import Any, List
import random
import chess
from .agent import Agent


class RandomAgent(Agent):
    def __init__(self, seed: int | None = None) -> None:
        super().__init__(name="RandomAgent")
        self._rng = random.Random(seed)

    def select_move(self, board: Any) -> Any:
        """Select a legal move uniformly at random.

        Expects board.generate_legal_moves() or board.legal_moves to exist.
        """
        # Try different common APIs for retrieving legal moves
        moves = None
        if hasattr(board, "generate_legal_moves"):
            moves = list(board.generate_legal_moves())
        elif hasattr(board, "legal_moves"):
            lm = board.legal_moves
            moves = list(lm) if not isinstance(lm, list) else lm
        elif hasattr(board, "get_legal_moves"):
            moves = list(board.get_legal_moves())
        else:
            # Try python-chess Board or ChessBoard class
            if hasattr(board, "board") and isinstance(board.board, chess.Board):
                moves = list(board.board.legal_moves)
            else:
                raise AttributeError(
                    "Board object does not expose a legal-move generator.\n"
                    "Expected one of: generate_legal_moves(), legal_moves, get_legal_moves()."
                )

        if not moves:
            return None
        return self._rng.choice(moves)