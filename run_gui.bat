@echo off
REM Ten skrypt uruchamia aplikację Voice Note w trybie GUI,
REM używając bezpośrednio interpretera Python z wirtualnego środowiska.

REM Ustawienie ścieżki do katalogu, w którym znajduje się ten skrypt
set "SCRIPT_DIR=%~dp0"

REM Pełna ścieżka do interpretera Python w środowisku .venv
set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM Pełna ścieżka do głównego pliku aplikacji
set "MAIN_PY=%SCRIPT_DIR%main.py"

REM Sprawdzenie, czy interpreter Python istnieje
if not exist "%PYTHON_EXE%" (
    echo Interpreter Python nie zostal znaleziony w: %PYTHON_EXE%
    echo.
    echo Upewnij sie, ze wirtualne srodowisko .venv zostalo utworzone.
    echo Uruchom 'python -m venv .venv' i 'pip install -r requirements.txt'
    pause
    exit /b
)

REM Uruchomienie aplikacji za pomocą pełnej ścieżki do interpretera
echo Uruchamianie Voice Note...
"%PYTHON_EXE%" "%MAIN_PY%" --gui

REM Jeśli wystąpił błąd, zatrzymaj okno terminala
if errorlevel 1 (
    echo.
    echo Wystapil blad podczas uruchamiania aplikacji.
    pause
)