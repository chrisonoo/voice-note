# Ten plik służy jako centralne miejsce do zarządzania wszystkimi ustawieniami aplikacji.
# Dzięki temu, jeśli chcesz coś zmienić (np. model AI), robisz to tylko tutaj.

import os
import tempfile

# --- GŁÓWNA NAZWA APLIKACJI ---
APP_NAME = "Voice Note"

# --- KATALOG TYMCZASOWY ---
# Tworzymy unikalny folder tymczasowy dla każdej sesji aplikacji.
# Ten folder będzie przechowywał wszystkie pliki robocze.
# Jest to lepsze rozwiązanie niż stały folder `rec/`, ponieważ unika konfliktów
# i ułatwia sprzątanie po zakończeniu pracy.
SESSION_TEMP_DIR = tempfile.mkdtemp(prefix=f"{APP_NAME.lower().replace(' ', '_')}_")

# --- ŚCIEŻKI DO KATALOGÓW WEWNĄTRZ FOLDERU TYMCZASOWEGO ---
# Definiujemy podfoldery wewnątrz naszego głównego folderu tymczasowego.
# `os.path.join` to bezpieczny sposób łączenia ścieżek, który działa na różnych systemach.
# W naszej nowej logice, `INPUT_DIR` nie jest już potrzebny, ponieważ pliki
# będą kopiowane bezpośrednio do folderu tymczasowego.
OUTPUT_DIR = os.path.join(SESSION_TEMP_DIR, 'output_wav')

# Tworzymy podfolder na przekonwertowane pliki .wav.
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- ŚCIEŻKI DO PLIKÓW STANU ---
# Pliki te również znajdują się w głównym folderze tymczasowym, co zapewnia,
# że stan aplikacji jest odizolowany dla każdej sesji.
AUDIO_LIST_TO_ENCODE_FILE = os.path.join(SESSION_TEMP_DIR, '1_audio_list_to_encode.txt')
AUDIO_LIST_TO_TRANSCRIBE_FILE = os.path.join(SESSION_TEMP_DIR, '2_audio_list_to_transcribe.txt')
PROCESSING_LIST_FILE = os.path.join(SESSION_TEMP_DIR, '3_processing_list.txt')
PROCESSED_LIST_FILE = os.path.join(SESSION_TEMP_DIR, '4_processed_list.txt')
TRANSCRIPTIONS_FILE = os.path.join(SESSION_TEMP_DIR, '5_transcriptions.txt')


# --- PARAMETRY TRANSKRYPCJI WHISPER ---
WHISPER_API_RESPONSE_FORMAT = "json"
WHISPER_API_TEMPERATURE = 0
WHISPER_API_PROMPT = ""


# --- USTAWIENIA ENKODOWANIA AUDIO ---
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']
FFMPEG_PARAMS = '-ac 1 -ar 44100'

# --- USTAWIENIA GUI ---
# Maksymalna długość pliku w sekundach, powyżej której plik zostanie oznaczony jako "długi".
# 5 minut = 300 sekund.
MAX_FILE_DURATION_SECONDS = 300