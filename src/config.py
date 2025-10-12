# Plik konfiguracyjny - serce ustawień aplikacji.
# Gromadzi w jednym miejscu wszystkie kluczowe parametry, które mogą wymagać modyfikacji.
# Dzięki takiemu podejściu, zmiana np. modelu AI czy ścieżek do folderów
# wymaga edycji tylko tego jednego pliku, co znacznie ułatwia zarządzanie projektem.

import os

# --- GŁÓWNA NAZWA APLIKACJI ---
# Zmienna przechowująca nazwę aplikacji, która może być wyświetlana np. w tytule okna.
APP_NAME = "Voice Note"

# --- GŁÓWNY KATALOG APLIKACJI ---
# Ta linia dynamicznie określa główny folder projektu.
# `__file__` to ścieżka do bieżącego pliku (config.py).
# `os.path.abspath` tworzy z tego pełną, absolutną ścieżkę.
# `os.path.dirname` usuwa ostatni komponent ścieżki (nazwę pliku), dając nam katalog `src`.
# Używamy `os.path.dirname` po raz drugi, aby "wyjść" z folderu `src` i znaleźć się w głównym katalogu projektu.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- KATALOGI ROBOCZE ---
# Definiujemy stałe ścieżki do folderów tymczasowych.
# Aplikacja będzie w nich przechowywać pliki pośrednie, np. przekonwertowane audio.
# Foldery te zostaną utworzone automatycznie w trakcie działania programu, jeśli nie istnieją.
TMP_DIR = os.path.join(APP_DIR, 'tmp')
AUDIO_TMP_DIR = os.path.join(APP_DIR, 'tmp', 'audio')

# --- BAZA DANYCH ---
# Używamy lekkiej bazy danych SQLite do przechowywania informacji o plikach i ich stanie.
# Poniżej definiujemy nazwę pliku bazy danych oraz pełną ścieżkę do niego.
DATABASE_FILENAME = f"{APP_NAME.lower().replace(' ', '_')}.db"
DATABASE_FILE = os.path.join(TMP_DIR, DATABASE_FILENAME)
# Flaga do włączania/wyłączania logowania (wyświetlania w konsoli) operacji na bazie danych.
# Przydatne podczas debugowania.
DATABASE_LOGGING = False


# --- PARAMETRY TRANSKRYPCJI WHISPER ---
# Ustawienia przekazywane bezpośrednio do API OpenAI Whisper.
# `response_format`: Określa format, w jakim chcemy otrzymać odpowiedź. "json" jest łatwy do przetwarzania.
WHISPER_API_RESPONSE_FORMAT = "json"
# `temperature`: Parametr kontrolujący "kreatywność" modelu. Wartość 0 oznacza najbardziej deterministyczne i powtarzalne wyniki.
WHISPER_API_TEMPERATURE = 0
# `prompt`: Opcjonalny tekst, który można przekazać modelowi, aby poprawić jakość transkrypcji,
# np. podając specyficzne terminy lub imiona.
WHISPER_API_PROMPT = ""


# --- USTAWIENIA KODOWANIA AUDIO ---
# Lista rozszerzeń plików, które aplikacja będzie traktować jako pliki audio.
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']
# Parametry dla narzędzia FFMPEG, używanego do konwersji audio.
# `-ac 1`: Ustawia jeden kanał audio (mono).
# `-ar 16000`: Ustawia częstotliwość próbkowania na 16000 Hz.
# `-af loudnorm=I=-12:TP=-1.0:LRA=7:dual_mono=true`: Normalizacja głośności.
# `-c:a aac`: Kodek AAC.
# `-b:a 24k`: Bitrate 24kbps.
# Te ustawienia są zoptymalizowane dla API OpenAI Whisper.
FFMPEG_PARAMS = '-ac 1 -ar 16000 -af loudnorm=I=-12:TP=-1.0:LRA=7:dual_mono=true -c:a aac -b:a 24k'

# --- USTAWIENIA INTERFEJSU GRAFICZNEGO (GUI) ---
# Maksymalna dopuszczalna długość pliku w sekundach.
# Pliki dłuższe niż ta wartość zostaną specjalnie oznaczone w interfejsie.
# Domyślnie ustawione na 5 minut (5 * 60 = 300 sekund).
MAX_FILE_DURATION_SECONDS = 300