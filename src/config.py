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
TMP_DIR = os.path.join(APP_DIR, 'tmp')
OUTPUT_DIR = os.path.join(TMP_DIR, 'output_wav')

# Tworzymy wszystkie potrzebne foldery przy starcie, jeśli nie istnieją.
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- NAZWY PLIKÓW STANU ---
# Nazwy plików przechowujących listy na różnych etapach procesu.
# Definiowane jako stałe, aby były spójne w całej aplikacji.
SELECTED_FILENAME = '1_selected.txt'
LOADED_FILENAME = '2_audio_list_to_transcribe.txt'
PROCESSING_FILENAME = '3_processing_list.txt'
PROCESSED_FILENAME = '4_processed_list.txt'
TRANSCRIPTIONS_FILENAME = '5_transcriptions.txt'

# --- ŚCIEŻKI DO PLIKÓW STANU ---
# Pliki przechowujące listy plików na różnych etapach procesu.
# Umieszczamy je w folderze `tmp`, aby były trwałe, ale ignorowane przez Git.
SELECTED_LIST = os.path.join(TMP_DIR, SELECTED_FILENAME)
LOADED_LIST = os.path.join(TMP_DIR, LOADED_FILENAME)
PROCESSING_LIST = os.path.join(TMP_DIR, PROCESSING_FILENAME)
PROCESSED_LIST = os.path.join(TMP_DIR, PROCESSED_FILENAME)
TRANSCRIPTIONS = os.path.join(TMP_DIR, TRANSCRIPTIONS_FILENAME)
 


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