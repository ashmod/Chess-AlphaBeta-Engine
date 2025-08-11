import json
import os
import datetime
import chess
import chess.pgn
from io import StringIO
from .board import ChessBoard
from .move import ChessMove

class GameIO:
    """
    Handles saving and loading chess games in various formats.
    """
    
    @staticmethod
    def _get_timestamp():
        """Get a formatted timestamp for file naming."""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    @staticmethod
    def save_game_as_json(game_data, filepath):
        """
        Save a game as a JSON file.
        
        Args:
            game_data (dict): Game data to save.
            filepath (str): Path to save the file to.
            
        Returns:
            bool: True if the save was successful, False otherwise.
        """
        try:
            # Ensure we're saving to the top-level replays folder, not a subdirectory
            if filepath.startswith('replays') and '\\' in filepath[8:]:  # After 'replays\'
                base_dir = 'replays'
                filename = os.path.basename(filepath)
                filepath = os.path.join(base_dir, filename)
                
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(game_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False
    
    @staticmethod
    def load_game_from_json(filepath):
        """
        Load a game from a JSON file.
        
        Args:
            filepath (str): Path to load the file from.
            
        Returns:
            dict: Game data, or None if loading failed.
        """
        try:
            print(f"Attempting to load game from: {filepath}")
            with open(filepath, 'r') as f:
                game_data = json.load(f)
                
            # Validate that we have moves in the data
            if "moves" in game_data:
                print(f"Successfully loaded game with {len(game_data['moves'])} moves")
                print(f"First few moves: {game_data['moves'][:min(5, len(game_data['moves']))]}")
            else:
                print(f"Warning: Loaded game data doesn't contain moves")
                
            return game_data
        except json.JSONDecodeError as je:
            print(f"JSON decode error loading game from {filepath}: {je}")
            return None
        except FileNotFoundError as fe:
            print(f"File not found: {filepath}")
            return None
        except Exception as e:
            print(f"Error loading game: {e}")
            return None
    
    @staticmethod
    def create_game_data(board, moves, white_player, black_player, result=None, event=None):
        """
        Create a game data dictionary for saving.
        
        Args:
            board: A ChessBoard object with the final position.
            moves: List of moves made in the game (as ChessMove objects or UCI strings).
            white_player (str): Name of the white player.
            black_player (str): Name of the black player.
            result (str, optional): Result of the game.
            event (str, optional): Name of the event.
            
        Returns:
            dict: Game data.
        """
        if result is None:
            result = board.get_result()
            
        # Convert moves to UCI format if they're ChessMove objects
        uci_moves = [move.get_uci() if isinstance(move, ChessMove) else move for move in moves]
        
        # Create a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "event": event or "Casual Game",
            "date": datetime.datetime.now().strftime("%Y.%m.%d"),
            "white": white_player,
            "black": black_player,
            "result": result,
            "moves": uci_moves,
            "final_position": board.get_fen(),
            "timestamp": timestamp
        }
    
    @staticmethod
    def save_replay(replay_data, filepath):
        """
        Save a game replay.
        
        Args:
            replay_data (dict): Replay data to save.
            filepath (str): Path to save the file to.
            
        Returns:
            bool: True if the save was successful, False otherwise.
        """
        return GameIO.save_game_as_json(replay_data, filepath)
    
    @staticmethod
    def load_replay(filepath):
        """
        Load a game replay.
        
        Args:
            filepath (str): Path to load the file from.
            
        Returns:
            dict: Replay data, or None if loading failed.
        """
        return GameIO.load_game_from_json(filepath)
    
    @staticmethod
    def export_to_pgn(game_data, filepath=None):
        """
        Export a game to PGN format.
        
        Args:
            game_data (dict): Game data to export.
            filepath (str, optional): Path to save the file to. If None, returns the PGN as a string.
            
        Returns:
            str or bool: PGN string if filepath is None, otherwise True if the export was successful.
        """
        try:
            # Create a new chess game
            game = chess.pgn.Game()
            
            # Set headers
            game.headers["Event"] = game_data.get("event", "?")
            game.headers["Date"] = game_data.get("date", "????.??.??")
            game.headers["White"] = game_data.get("white", "?")
            game.headers["Black"] = game_data.get("black", "?")
            game.headers["Result"] = game_data.get("result", "*")
            
            # Create a board and add the moves
            board = chess.Board()
            node = game
            
            for uci_move in game_data.get("moves", []):
                move = chess.Move.from_uci(uci_move)
                node = node.add_variation(move)
                board.push(move)
            
            # Write to file or return as string
            if filepath:
                # Create the directory if it doesn't exist
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'w') as f:
                    print(game, file=f, end="\n\n")
                return True
            else:
                output = StringIO()
                print(game, file=output, end="\n\n")
                return output.getvalue()
                
        except Exception as e:
            print(f"Error exporting to PGN: {e}")
            return False if filepath else ""
    
    @staticmethod
    def import_from_pgn(pgn_string=None, filepath=None):
        """
        Import a game from PGN format.
        
        Args:
            pgn_string (str, optional): PGN string to import.
            filepath (str, optional): Path to load the file from.
            
        Returns:
            dict: Game data, or None if import failed.
        """
        try:
            if filepath:
                with open(filepath, 'r') as f:
                    pgn_io = StringIO(f.read())
            elif pgn_string:
                pgn_io = StringIO(pgn_string)
            else:
                return None
                
            # Read the game
            game = chess.pgn.read_game(pgn_io)
            if game is None:
                return None
                
            # Extract game information
            white_player = game.headers.get("White", "?")
            black_player = game.headers.get("Black", "?")
            event = game.headers.get("Event", "?")
            date = game.headers.get("Date", "????.??.??")
            result = game.headers.get("Result", "*")
            
            # Extract moves
            moves = []
            board = chess.Board()
            
            # Traverse the move tree
            node = game
            while node.variations:
                node = node.variations[0]  # Follow the main line
                move = node.move
                moves.append(move.uci())
                board.push(move)
            
            # Create game data
            game_data = {
                "event": event,
                "date": date,
                "white": white_player,
                "black": black_player,
                "result": result,
                "moves": moves,
                "final_position": board.fen(),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return game_data
            
        except Exception as e:
            print(f"Error importing from PGN: {e}")
            return None