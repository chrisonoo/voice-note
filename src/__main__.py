#!/usr/bin/env python3
"""
Main entry point for the voice-note application when run as a module.
"""

import os
import sys

# Add the project root to Python path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import main as _main


def main():
    """Entry point function for console script."""
    _main()


if __name__ == "__main__":
    main()
