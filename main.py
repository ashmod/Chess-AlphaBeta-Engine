#!/usr/bin/env python3
"""
CLI Version.
**** Version 1.0.0 ****

Chess-AlphaBeta-Engine: A chess game with AI support and replay functionality.
Main entry point to launch the chess game.
"""

import os
import sys
import argparse

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main entry point for the chess engine."""
    parser = argparse.ArgumentParser(description='Chess game with AI support and replay functionality.')
    parser.add_argument('--no-gui', action='store_true', help='Run in text mode (no GUI)')
    parser.add_argument('--replay', type=str, help='Load and replay a saved game file')
    parser.add_argument('--ai', choices=['random', 'alphabeta'], default='random', 
                      help='AI algorithm to use in CLI/text mode (default: random)')
    parser.add_argument('--depth', type=int, default=3,
                      help='Search depth for alphabeta AI (default: 3)')
    args = parser.parse_args()
    
    # Check if dependencies are installed
    try:
        import chess
    except ImportError:
        print("Python-chess package not found. Please run setup.py first.")
        sys.exit(1)
    
    if args.no_gui:
        # Text-based mode
        from src.core.board import ChessBoard
        from src.core.game_io import GameIO
        
        # Select AI agent
        if args.ai == 'random':
            from src.ai.random_agent import RandomAgent
            ai = RandomAgent()
            print(f"Using Random AI")
        else:  # alphabeta
            from src.ai.alpha_beta import AlphaBetaAgent
            ai = AlphaBetaAgent(depth=args.depth)
            print(f"Using AlphaBeta AI with depth {args.depth}")
        
        # Initialize game
        board = ChessBoard()
        
        # Simple text-based game loop
        print("Chess Game (Text Mode)")
        print("Enter moves in UCI format (e.g., e2e4) or 'quit' to exit")
        
        while not board.is_game_over():
            # Display board
            print("\n" + str(board))
            print(f"Turn: {'White' if board.board.turn else 'Black'}")
            
            if board.board.turn:  # Human's turn (White)
                move_uci = input("Your move: ")
                if move_uci.lower() == 'quit':
                    break
                
                if not board.make_move(move_uci):
                    print("Invalid move! Try again.")
                    continue
            else:  # AI's turn (Black)
                print("AI is thinking...")
                ai_move = ai.get_move(board)
                board.make_move(ai_move)
                print(f"AI plays: {ai_move}")
            
            # Check game status
            if board.is_check():
                print("CHECK!")
            
        # Game over
        print("\nGame over!")
        print(f"Result: {board.get_result()}")
        
        # Save game
        save = input("Save replay? (y/n): ")
        if save.lower() == 'y':
            replay_file = os.path.join('replays', f"game_{GameIO._get_timestamp()}.json")
            GameIO.save_replay({
                "moves": [m.uci() for m in board.board.move_stack],
                "result": board.get_result(),
                "white": "Human",
                "black": f"AI ({args.ai})",
                "event": "Text Mode Game"
            }, replay_file)
            print(f"Game saved to {replay_file}")
    
    elif args.replay:
        # Replay mode
        from src.core.game_io import GameIO
        from src.gui.game_ui import ReplayViewer
        
        # Load replay
        replay_data = GameIO.load_replay(args.replay)
        if replay_data:
            print(f"Loaded replay: {args.replay}")
            ReplayViewer(replay_data).run()
        else:
            print(f"Failed to load replay: {args.replay}")
    
    else:
        # GUI mode with start screen
        from src.gui import App
        App().run()

if __name__ == "__main__":
    main()