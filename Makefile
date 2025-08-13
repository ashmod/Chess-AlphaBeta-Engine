# Makefile for Chess-AlphaBeta-Engine
# Provides convenient commands for running the chess engine with different configurations

.PHONY: help install dev-install clean run gui cli test lint format setup venv

# Default Python command
PYTHON := python3
PIP := pip3

# Virtual environment
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# Help command - displays available targets
help:
	@echo "Chess-AlphaBeta-Engine Makefile"
	@echo "================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  venv          Create virtual environment"
	@echo "  install       Install dependencies"
	@echo "  dev-install   Install with development dependencies"
	@echo "  setup         Full setup (venv + install)"
	@echo ""
	@echo "Run Commands (GUI Mode):"
	@echo "  run           Run GUI with Random AI (default)"
	@echo "  gui           Same as 'run'"
	@echo "  gui-alphabeta Run GUI with Alpha-Beta AI (depth 3)"
	@echo "  gui-deep      Run GUI with Alpha-Beta AI (depth 5)"
	@echo ""
	@echo "Run Commands (CLI Mode):"
	@echo "  cli           Run CLI with Random AI"
	@echo "  cli-alphabeta Run CLI with Alpha-Beta AI (depth 3)"
	@echo "  cli-deep      Run CLI with Alpha-Beta AI (depth 5)"
	@echo ""
	@echo "Replay Commands:"
	@echo "  replay FILE=<path>  Replay a saved game file"
	@echo "  Example: make replay FILE=replays/example_game.json"
	@echo ""
	@echo "Development Commands:"
	@echo "  test          Run tests (if available)"
	@echo "  lint          Run code linting"
	@echo "  format        Format code with black"
	@echo "  clean         Clean up build artifacts"
	@echo ""
	@echo "Package Commands:"
	@echo "  build         Build package"
	@echo "  install-pkg   Install package in development mode"

# Setup Commands
venv:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Virtual environment created in $(VENV_DIR)"

install:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt

dev-install:
	@echo "Installing with development dependencies..."
	$(PIP) install -e .[dev]

setup: venv
	@echo "Setting up development environment..."
	$(VENV_PIP) install -r requirements.txt
	@echo "Setup complete! Activate with: source $(VENV_DIR)/bin/activate"

# Run Commands - GUI Mode
run: gui

gui:
	@echo "Starting Chess Engine (GUI mode with Random AI)..."
	$(PYTHON) main.py

gui-alphabeta:
	@echo "Starting Chess Engine (GUI mode with Alpha-Beta AI, depth 3)..."
	$(PYTHON) main.py --ai alphabeta --depth 3

gui-deep:
	@echo "Starting Chess Engine (GUI mode with Alpha-Beta AI, depth 5)..."
	$(PYTHON) main.py --ai alphabeta --depth 5

# Run Commands - CLI Mode
cli:
	@echo "Starting Chess Engine (CLI mode with Random AI)..."
	$(PYTHON) main.py --no-gui --ai random

cli-alphabeta:
	@echo "Starting Chess Engine (CLI mode with Alpha-Beta AI, depth 3)..."
	$(PYTHON) main.py --no-gui --ai alphabeta --depth 3

cli-deep:
	@echo "Starting Chess Engine (CLI mode with Alpha-Beta AI, depth 5)..."
	$(PYTHON) main.py --no-gui --ai alphabeta --depth 5

# Replay Commands
replay:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make replay FILE=<path_to_replay_file>"; \
		echo "Example: make replay FILE=replays/example_game.json"; \
		exit 1; \
	fi
	@echo "Replaying game from $(FILE)..."
	$(PYTHON) main.py --replay $(FILE)

# Development Commands
test:
	@echo "Running tests..."
	@if [ -f "pytest.ini" ] || [ -d "tests" ]; then \
		$(PYTHON) -m pytest; \
	else \
		echo "No tests found. Create tests/ directory or pytest.ini to enable testing."; \
	fi

lint:
	@echo "Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ main.py; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi

format:
	@echo "Formatting code with black..."
	@if command -v black >/dev/null 2>&1; then \
		black src/ main.py move_replays.py; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

# Package Commands
build:
	@echo "Building package..."
	$(PYTHON) setup.py sdist bdist_wheel

install-pkg:
	@echo "Installing package in development mode..."
	$(PIP) install -e .

# Cleanup Commands
clean:
	@echo "Cleaning up build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	@echo "Cleanup complete!"

# Quick development shortcuts
dev: setup dev-install
	@echo "Development environment ready!"

play: gui
play-hard: gui-deep
text: cli
text-hard: cli-deep
