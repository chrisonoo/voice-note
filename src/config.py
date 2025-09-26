# Ten plik służy jako centralne miejsce do zarządzania wszystkimi ustawieniami aplikacji.
# Dzięki temu, jeśli chcesz coś zmienić (np. model AI), robisz to tylko tutaj.

import os

# --- GŁÓWNA NAZWA APLIKACJI ---
APP_NAME = "Voice Note"

# --- GŁÓWNY KATALOG APLIKACJI ---
# Używamy os.path.abspath, aby uzyskać pełną ścieżkę do pliku,
# a następnie dirname, aby znaleźć katalog, w którym się znajduje.
# Robimy to dwukrotnie, aby cofnąć się z `src` do głównego folderu projektu.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- KATALOGI ROBOCZE ---
# Używamy stałych folderów, aby stan aplikacji był zachowywany po jej zamknięciu.
# Foldery będą tworzone dynamicznie gdy będą potrzebne
TMP_DIR = os.path.join(APP_DIR, 'tmp')
AUDIO_TMP_DIR = os.path.join(APP_DIR, 'tmp', 'audio')

# --- BAZA DANYCH ---
# Używamy bazy danych SQLite do przechowywania stanu aplikacji.
# Plik bazy danych jest tworzony w folderze tymczasowym i usuwany przy każdym uruchomieniu.
DATABASE_FILENAME = f"{APP_NAME.lower().replace(' ', '_')}.db"
DATABASE_FILE = os.path.join(TMP_DIR, DATABASE_FILENAME)
DATABASE_LOGGING = False # Ustaw na True, aby logować operacje na bazie danych


# --- PARAMETRY TRANSKRYPCJI WHISPER ---
WHISPER_API_RESPONSE_FORMAT = "json"
WHISPER_API_TEMPERATURE = 0
WHISPER_API_PROMPT = ""


# --- AUDIO ENCODING SETTINGS ---
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']
FFMPEG_PARAMS = '-ac 1 -ar 44100'

# --- USTAWIENIA GUI ---
# Maksymalna długość pliku w sekundach, powyżej której plik zostanie oznaczony jako "długi".
# 5 minut = 300 sekund.
MAX_FILE_DURATION_SECONDS = 300