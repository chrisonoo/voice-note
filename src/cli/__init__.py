"""
CLI entry point module for Voice Note application.
This module provides the main entry point for the command line interface.
"""

import argparse

from src import database

from .main_cli import main_cli


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for CLI mode.

    Args:
        args: Parsed command line arguments object
    """
    database.initialize_database()
    main_cli(args)
