"""
GUI entry point module for Voice Note application.
This module provides the main entry point for the graphical user interface.
"""

from src import database

from .core import main_gui


def main():
    """
    Main entry point for GUI mode.
    Initializes database and starts the GUI application.
    """
    database.initialize_database()
    main_gui.main()
