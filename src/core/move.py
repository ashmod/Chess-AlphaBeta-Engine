import chess

class ChessMove:
    """
    A wrapper around the python-chess Move class.
    """
    def __init__(self, move):
        """
        Initialize a new chess move.
        
        Args:
            move: A chess.Move object or a move in UCI format (e.g., "e2e4").
        """
        if isinstance(move, chess.Move):
            self.move = move
        elif isinstance(move, str):
            try:
                self.move = chess.Move.from_uci(move)
            except ValueError:
                raise ValueError(f"Invalid move format: {move}")
        else:
            raise TypeError("Move must be a chess.Move object or a UCI string")
    
    @classmethod
    def from_squares(cls, from_square, to_square, promotion=None):
        """
        Create a move from source and destination squares.
        
        Args:
            from_square (str or int): Source square (e.g., "e2" or chess.E2).
            to_square (str or int): Destination square (e.g., "e4" or chess.E4).
            promotion (str or None): Piece to promote to (e.g., "q" for queen).
            
        Returns:
            ChessMove: A new move object.
        """
        # Convert string squares to integers if necessary
        if isinstance(from_square, str):
            from_square = chess.parse_square(from_square)
        if isinstance(to_square, str):
            to_square = chess.parse_square(to_square)
            
        # Handle promotion
        if promotion:
            if isinstance(promotion, str):
                promotion = chess.Piece.from_symbol(promotion).piece_type
            move = chess.Move(from_square, to_square, promotion)
        else:
            move = chess.Move(from_square, to_square)
            
        return cls(move)
    
    def get_uci(self):
        """
        Get the UCI notation for this move.
        
        Returns:
            str: Move in UCI format (e.g., "e2e4").
        """
        return self.move.uci()
    
    def get_san(self, board):
        """
        Get the Standard Algebraic Notation (SAN) for this move.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            str: Move in SAN format (e.g., "e4" or "Nf3").
        """
        return board.board.san(self.move)
    
    def is_capture(self, board):
        """
        Check if this move is a capture.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the move is a capture, False otherwise.
        """
        return board.board.is_capture(self.move)
    
    def is_castling(self, board):
        """
        Check if this move is a castling move.
        
        Args:
            board: A ChessBoard object.
            
        Returns:
            bool: True if the move is a castling move, False otherwise.
        """
        return board.board.is_castling(self.move)
    
    def __str__(self):
        """
        String representation of the move.
        
        Returns:
            str: Move in UCI format.
        """
        return self.get_uci()
    
    def __eq__(self, other):
        """
        Check if two moves are equal.
        
        Args:
            other: Another ChessMove object or a string in UCI format.
            
        Returns:
            bool: True if the moves are equal, False otherwise.
        """
        if isinstance(other, ChessMove):
            return self.move == other.move
        elif isinstance(other, str):
            return self.get_uci() == other
        elif isinstance(other, chess.Move):
            return self.move == other
        return False