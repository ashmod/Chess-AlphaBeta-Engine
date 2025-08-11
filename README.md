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

## Quick Start (GUI)
Install dependencies:

```
pip install -r requirements.txt  # or use conda env then pip for python-chess
```

Run GUI (default AlphaBeta depth 3):
```
python main.py
```

Options:
```
python main.py --ai random          # Use Random AI
python main.py --depth 4            # Deeper alpha-beta search
python main.py --no-gui             # Text/CLI mode
python main.py --replay replays/example_game.json  # View saved replay
```

## GUI Controls
- Left click: select piece then destination square
- Buttons (right panel): New Game, Undo, Quit
- Replay viewer: Arrow Left/Right step, Space play/pause

## Saving Replays (CLI Mode)
After a text-mode game you'll be prompted to save; files go to `replays/`.
GUI saving (button/export) can be added next if needed.

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
