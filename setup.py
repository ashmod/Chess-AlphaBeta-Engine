#!/usr/bin/env python3
"""
Setup script for Chess-AlphaBeta-Engine.

This package provides an interactive chess engine with Alpha-Beta AI,
Random AI, text mode, GUI, and replay viewer functionality.
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    """Read README.md for long description."""
    here = os.path.abspath(os.path.dirname(__file__))
    readme_path = os.path.join(here, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Interactive chess engine with Alpha-Beta AI, Random AI, text mode, GUI, and replay viewer."

# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt."""
    here = os.path.abspath(os.path.dirname(__file__))
    requirements_path = os.path.join(here, 'requirements.txt')
    requirements = []
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    requirements.append(line)
    return requirements

setup(
    name="chess-alphabeta-engine",
    version="1.0.0",
    author="dizzydroid",
    author_email="",  # Add your email if desired
    description="Interactive chess engine with Alpha-Beta AI, Random AI, text mode, GUI, and replay viewer",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/dizzydroid/Chess-AlphaBeta-Engine",
    project_urls={
        "Bug Tracker": "https://github.com/dizzydroid/Chess-AlphaBeta-Engine/issues",
        "Source Code": "https://github.com/dizzydroid/Chess-AlphaBeta-Engine",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Board Games",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",  # Update if different license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.900",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "chess-engine=main:main",
            "chess-alphabeta=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "gui": ["assets/**/*"],
    },
    keywords=[
        "chess",
        "game",
        "ai",
        "alpha-beta",
        "minimax",
        "pygame",
        "gui",
        "engine",
        "board-game",
        "artificial-intelligence",
    ],
    zip_safe=False,
)
