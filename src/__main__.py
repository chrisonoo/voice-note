#!/usr/bin/env python3
"""
Main entry point for the voice-note application when run as a module.
This handles command line argument parsing and launches appropriate mode (GUI or CLI).
"""

import argparse
import os
import sys

# Add the project root to Python path so we can import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.cli import main as main_cli
from src.gui import main as main_gui


def main():
    """
    Main entry point for the voice-note application.
    Handles both CLI and GUI modes depending on provided arguments.
    """
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Transkrypcja plików audio z użyciem API OpenAI Whisper."
    )

    # Add arguments
    parser.add_argument(
        "-l",
        "--allow-long",
        action="store_true",
        help="Zezwól na przetwarzanie dłuższych plików (tylko tryb CLI).",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Uruchom aplikację w trybie graficznego interfejsu użytkownika (GUI).",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Ścieżka do folderu zawierającego pliki audio do transkrypcji (tylko tryb CLI).",
    )

    # Parse arguments
    args = parser.parse_args()

    # Check if user provided --gui flag
    if args.gui:
        # Launch GUI mode
        main_gui()
    else:
        # Launch CLI mode with parsed arguments
        main_cli(args)


if __name__ == "__main__":
    main()
