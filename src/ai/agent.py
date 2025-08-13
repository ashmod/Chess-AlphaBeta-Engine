"""
Agent base class and common utilities for AI agents.
"""
from __future__ import annotations
from typing import Any, Iterable, List, Optional
import abc
import chess


class Agent(abc.ABC):
    """
    Abstract base class for AI agents.
    """
    def __init__(self, name: str = "Agent") -> None:
        self.name = name

    @abc.abstractmethod
    def select_move(self, board: Any) -> Any:
        """Return a move object chosen for the given board state.
        """
        raise NotImplementedError
        
    def get_move(self, board: Any) -> str:
        """Get a move for the current board state in UCI format.
        
        This is a convenience method that returns a move in UCI format,
        which can be directly used with the ChessBoard.make_move method.
        
        Args:
            board: A ChessBoard object or any object with compatible interface.
            
        Returns:
            str: A move in UCI format (e.g., "e2e4").
        """
        move = self.select_move(board)
        if isinstance(move, chess.Move):
            return move.uci()
        elif hasattr(move, "move") and isinstance(move.move, chess.Move):
            return move.move.uci()
        elif hasattr(move, "uci"):
            return move.uci()
        elif hasattr(move, "get_uci"):
            return move.get_uci()
        else:
            return str(move)