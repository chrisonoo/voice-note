@echo off
REM Ten skrypt aktywuje wirtualne środowisko i uruchamia aplikację Voice Note w trybie GUI.

REM Ustawienie ścieżki do katalogu, w którym znajduje się ten skrypt
set SCRIPT_DIR=%~dp0

REM Ścieżka do skryptu aktywującego .venv
set VENV_ACTIVATE=%SCRIPT_DIR%.venv\Scripts\activate.bat

REM Sprawdzenie, czy .venv istnieje
if not exist "%VENV_ACTIVATE%" (
    echo Wirtualne srodowisko (.venv) nie zostalo znalezione.
    echo Uruchom 'python -m venv .venv' i 'pip install -r requirements.txt'
    pause
    exit /b
)

REM Aktywacja środowiska i uruchomienie aplikacji
call "%VENV_ACTIVATE%"
echo Uruchamianie Voice Note...
python "%SCRIPT_DIR%main.py" --gui