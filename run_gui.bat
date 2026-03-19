@echo off
REM Launches Voice Note GUI via UV. Console stays hidden when run from run_silent.vbs.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

uv run python main.py --gui