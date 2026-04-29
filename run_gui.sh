#!/usr/bin/env bash
# Linux launcher for voice_note (WSLg)
# Self-contained: works under interactive shell, `wsl.exe -- bash -lc`, cron, etc.
set -e

cd "$(dirname "$0")"

# Ensure uv is reachable regardless of how this script is invoked.
export PATH="$HOME/.local/uv:$HOME/.local/bin:$PATH"

exec uv run python main.py --gui
