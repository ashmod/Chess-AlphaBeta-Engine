# Chess-AlphaBeta-Engine
Interactive chess engine with Alpha-Beta AI, Random AI, text mode, GUI, and replay viewer.

## Features
- Human vs AI (Random or Alpha-Beta) from GUI or CLI
- Click-based board interaction (no drag yet)
- Legal move highlighting & last-move highlighting
- Check highlighting (king square turns red)
- Automatic queen promotion
- Undo (rewinds a full move pair) & New Game buttons
- Replay viewer for saved JSON games (arrow keys to navigate)

## Quick Start

### Using Makefile (Recommended)
The easiest way to get started is using the included Makefile:

```bash
# Setup (creates virtual environment and installs dependencies)
make setup

# Run the game
make run              # GUI with Random AI
make gui-alphabeta    # GUI with Alpha-Beta AI (depth 3)
make gui-deep         # GUI with deeper Alpha-Beta search (depth 5)

# CLI mode
make cli              # Text mode with Random AI
make cli-alphabeta    # Text mode with Alpha-Beta AI
make cli-deep         # Text mode with deeper search

# Replay saved games
make replay FILE=replays/example_game.json

# Quick shortcuts
make play             # Same as 'run'
make play-hard        # Hard difficulty (depth 5)
```

Run `make help` to see all available commands.

### Manual Setup
If you prefer manual setup:

```bash
# Install dependencies
pip install -r requirements.txt  # or use conda env then pip for python-chess

# Run GUI (default Random AI)
python main.py

# Command line options
python main.py --ai alphabeta --depth 3    # Alpha-Beta AI
python main.py --ai random                 # Random AI  
python main.py --depth 4                   # Deeper alpha-beta search
python main.py --no-gui                    # Text/CLI mode
python main.py --replay replays/example_game.json  # View saved replay
```

## GUI Controls
- Left click: select piece then destination square
- Buttons (right panel): New Game, Undo, Quit
- Replay viewer: Arrow Left/Right step, Space play/pause

## Saving Replays (CLI Mode)
After a text-mode game you'll be prompted to save; files go to `replays/`.
GUI saving (button/export) can be added next if needed.

## Development

### Package Installation
You can install the chess engine as a Python package:

```bash
# Development installation (editable)
make dev-install
# or manually:
pip install -e .

# This creates console commands:
chess-engine          # Same as 'python main.py'
chess-alphabeta       # Same as 'python main.py'
```

### Development Tools
```bash
make lint             # Code linting with flake8
make format           # Code formatting with black  
make clean            # Clean build artifacts
make build            # Build package for distribution
```

## Project Layout
`src/core` board & rules wrappers (python-chess backend)
`src/ai` agents (Random and AlphaBeta) and evaluation
`src/gui` Pygame GUI implementation
`replays/` saved game JSON files

## Next Improvements (Ideas)
- Drag-and-drop moves
- In-GUI save/export (JSON & PGN)
- Promotion piece selection dialog
- Configurable AI side / Human vs Human mode
- Move annotation & PGN export from GUI

## License
See `LICENSE`.
