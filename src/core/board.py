import chess
import numpy as np

class ChessBoard:
    """
    A wrapper around the python-chess Board class that adds functionality
    specific to our application.
    """
    def __init__(self, fen=None):
        """
        Initialize a new chess board, optionally from a FEN string.
        
        Args:
            fen (str, optional): FEN string representation of a board position.
        """
        self.board = chess.Board(fen) if fen else chess.Board()
        
    def get_legal_moves(self):
        """
        Returns a list of legal moves in the current position.
        
        Returns:
            list: Legal moves in the current position.
        """
        return list(self.board.legal_moves)
    
    def make_move(self, move):
        """
        Make a move on the board.
        
        Args:
            move: A chess.Move object or a move in UCI format (e.g., "e2e4").
            
        Returns:
            bool: True if the move was made, False otherwise.
        """
        if isinstance(move, str):
            try:
                move = chess.Move.from_uci(move)
            except ValueError:
                return False
                
        if move in self.board.legal_moves:
            self.board.push(move)
            return True
        return False
    
    def undo_move(self):
        """
        Undo the last move.
        
        Returns:
            chess.Move: The move that was undone, or None if no moves to undo.
        """
        try:
            return self.board.pop()
        except IndexError:
            return None
    
    def is_game_over(self):
        """
        Check if the game is over.
        
        Returns:
            bool: True if the game is over, False otherwise.
        """
        return self.board.is_game_over()
    
    def get_result(self):
        """
        Get the result of the game if it's over.
        
        Returns:
            str: "1-0" (white wins), "0-1" (black wins), "1/2-1/2" (draw), or "*" (ongoing).
        """
        if not self.is_game_over():
            return "*"
        return self.board.result()
    
    def is_check(self):
        """
        Check if the current position is a check.
        
        Returns:
            bool: True if the current position is a check, False otherwise.
        """
        return self.board.is_check()
    
    def is_checkmate(self):
        """
        Check if the current position is a checkmate.
        
        Returns:
            bool: True if the current position is a checkmate, False otherwise.
        """
        return self.board.is_checkmate()
    
    def is_stalemate(self):
        """
        Check if the current position is a stalemate.
        
        Returns:
            bool: True if the current position is a stalemate, False otherwise.
        """
        return self.board.is_stalemate()
    
    def get_fen(self):
        """
        Get the FEN string representation of the current position.
        
        Returns:
            str: FEN string.
        """
        return self.board.fen()
    
    def get_board_array(self):
        """
        Convert the board to a 2D numpy array for AI evaluation.
        
        Returns:
            numpy.ndarray: 8x8 array representing the board.
        """
        board_array = np.zeros((8, 8), dtype=np.int8)
        
        piece_values = {
            'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
            'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6
        }
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                row, col = 7 - (square // 8), square % 8
                board_array[row, col] = piece_values[piece.symbol()]
                
        return board_array
    
    def __str__(self):
        """
        String representation of the board.
        
        Returns:
            str: ASCII representation of the board.
        """
        return str(self.board)