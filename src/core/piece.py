import chess

class ChessPiece:
    """
    A wrapper around the python-chess Piece class.
    """
    
    # Constants for piece types
    PAWN = chess.PAWN
    KNIGHT = chess.KNIGHT
    BISHOP = chess.BISHOP
    ROOK = chess.ROOK
    QUEEN = chess.QUEEN
    KING = chess.KING
    
    # Constants for colors
    WHITE = chess.WHITE
    BLACK = chess.BLACK
    
    def __init__(self, piece_type, color):
        """
        Initialize a new chess piece.
        
        Args:
            piece_type (int): Type of the piece (e.g., ChessPiece.PAWN).
            color (bool): Color of the piece (ChessPiece.WHITE or ChessPiece.BLACK).
        """
        self.piece = chess.Piece(piece_type, color)
    
    @classmethod
    def from_symbol(cls, symbol):
        """
        Create a piece from a symbol.
        
        Args:
            symbol (str): Symbol of the piece (e.g., "P" for white pawn, "k" for black king).
            
        Returns:
            ChessPiece: A new piece object.
        """
        piece = chess.Piece.from_symbol(symbol)
        return cls(piece.piece_type, piece.color)
    
    def get_symbol(self):
        """
        Get the symbol for this piece.
        
        Returns:
            str: Symbol of the piece (e.g., "P" for white pawn, "k" for black king).
        """
        return self.piece.symbol()
    
    def get_name(self):
        """
        Get the name of this piece.
        
        Returns:
            str: Name of the piece (e.g., "white pawn", "black king").
        """
        color = "white" if self.piece.color else "black"
        piece_names = {
            chess.PAWN: "pawn",
            chess.KNIGHT: "knight",
            chess.BISHOP: "bishop",
            chess.ROOK: "rook",
            chess.QUEEN: "queen",
            chess.KING: "king"
        }
        return f"{color} {piece_names[self.piece.piece_type]}"
    
    def get_piece_type(self):
        """
        Get the type of this piece.
        
        Returns:
            int: Type of the piece.
        """
        return self.piece.piece_type
    
    def get_color(self):
        """
        Get the color of this piece.
        
        Returns:
            bool: Color of the piece (True for white, False for black).
        """
        return self.piece.color
    
    def is_white(self):
        """
        Check if this piece is white.
        
        Returns:
            bool: True if the piece is white, False otherwise.
        """
        return self.piece.color
    
    def is_black(self):
        """
        Check if this piece is black.
        
        Returns:
            bool: True if the piece is black, False otherwise.
        """
        return not self.piece.color
    
    def __str__(self):
        """
        String representation of the piece.
        
        Returns:
            str: Symbol of the piece.
        """
        return self.get_symbol()
    
    def __eq__(self, other):
        """
        Check if two pieces are equal.
        
        Args:
            other: Another ChessPiece object or a string symbol.
            
        Returns:
            bool: True if the pieces are equal, False otherwise.
        """
        if isinstance(other, ChessPiece):
            return self.piece == other.piece
        elif isinstance(other, str):
            return self.get_symbol() == other
        elif isinstance(other, chess.Piece):
            return self.piece == other
        return False