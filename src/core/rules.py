import chess
from .board import ChessBoard
from .move import ChessMove

class ChessRules:
    """
    Handles chess rules and game state validation.
    """
    
    @staticmethod
    def is_valid_move(board, move):
        """
        Check if a move is valid.
        
        Args:
            board: A ChessBoard object.
            move: A ChessMove object or a move in UCI format.
            
        Returns:
            bool: True if the move is valid, False otherwise.
        """
        if isinstance(move, str):
            try:
                move = chess.Move.from_uci(move)
            except ValueError:
                return False
        elif isinstance(move, ChessMove):
            move = move.move
            
        return move in board.board.legal_moves
    
    @staticmethod
    def get_valid_moves(board, square=None):
        """
        Get all valid moves from a specific square or for the entire board.
        
        Args:
            board: A ChessBoard object.
            square (str or int, optional): The square to get moves from (e.g., "e2" or chess.E2).
            
        Returns:
            list: List of valid moves as ChessMove objects.
        """
        if square is not None:
            if isinstance(square, str):
                square = chess.parse_square(square)
                
            moves = [move for move in board.board.legal_moves if move.from_square == square]
        else:
            moves = list(board.board.legal_moves)
            
        return [ChessMove(move) for move in moves]
    
    @staticmethod
    def is_check(board):
        """
        Check if the current position is a check.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the current position is a check, False otherwise.
        """
        return board.board.is_check()
    
    @staticmethod
    def is_checkmate(board):
        """
        Check if the current position is a checkmate.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the current position is a checkmate, False otherwise.
        """
        return board.board.is_checkmate()
    
    @staticmethod
    def is_stalemate(board):
        """
        Check if the current position is a stalemate.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the current position is a stalemate, False otherwise.
        """
        return board.board.is_stalemate()
    
    @staticmethod
    def is_insufficient_material(board):
        """
        Check if there is insufficient material to checkmate.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if there is insufficient material, False otherwise.
        """
        return board.board.is_insufficient_material()
    
    @staticmethod
    def is_game_over(board):
        """
        Check if the game is over.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the game is over, False otherwise.
        """
        return board.board.is_game_over()
    
    @staticmethod
    def get_game_result(board):
        """
        Get the result of the game if it's over.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            str: "1-0" (white wins), "0-1" (black wins), "1/2-1/2" (draw), or "*" (ongoing).
        """
        if not ChessRules.is_game_over(board):
            return "*"
        return board.board.result()
    
    @staticmethod
    def get_game_end_reason(board):
        """
        Get the reason why the game ended.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            str: Reason why the game ended, or None if the game is not over.
        """
        if not ChessRules.is_game_over(board):
            return None
            
        if board.board.is_checkmate():
            return "checkmate"
        elif board.board.is_stalemate():
            return "stalemate"
        elif board.board.is_insufficient_material():
            return "insufficient material"
        elif board.board.is_seventyfive_moves():
            return "75-move rule"
        elif board.board.is_fivefold_repetition():
            return "fivefold repetition"
        elif board.board.is_fifty_moves():
            return "50-move rule"
        elif board.board.is_threefold_repetition():
            return "threefold repetition"
        else:
            return "unknown"