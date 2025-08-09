"""
Agent base class and common utilities for AI agents.

ASSUMPTIONS about core.Board API (TODO: implement):
- board.generate_legal_moves() -> iterable of Move-like objects
- board.push(move) -> applies move
- board.pop() -> reverts last move
- board.is_checkmate() -> bool
- board.is_stalemate() -> bool
- board.turn -> 'white' or 'black' or True/False (truthy for white)
- Move objects must be usable by board.push() and comparable/equatable

"""
from __future__ import annotations
from typing import Any, Iterable, List, Optional
import abc


class Agent(abc.ABC):
    """Abstract base class for AI agents.

    Subclasses should implement select_move(board) and may accept
    configuration parameters in their constructors.
    """

    def __init__(self, name: str = "Agent") -> None:
        self.name = name

    @abc.abstractmethod
    def select_move(self, board: Any) -> Any:
        """Return a move object chosen for the given board state.

        The returned move must be a move object accepted by the
        core.Board.push(move) method used in your project.
        """
        raise NotImplementedError