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
# Lista rozszerzeń plików audio
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.wma']

# Lista rozszerzeń plików wideo (z możliwością ekstrakcji audio)
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']

# Wszystkie obsługiwane rozszerzenia (dla dialogu wyboru plików)
ALL_SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS
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

# --- SZEROKOŚCI PANELI I KOLUMN ---
# Szerokości paneli głównych
PANEL_SELECTED_WIDTH = 450          # Panel "Wybrane" (FilesView)
PANEL_STATUS_WIDTH = 150            # Panele statusu (Wczytane, Do przetworzenia, Przetworzone)
PANEL_TRANSCRIPTION_WIDTH = 350     # Panel "Transkrypcja"

# Szerokości kolumn w panelu "Wybrane"
COLUMN_CHECKBOX_WIDTH = 30          # Kolumna checkboxów
COLUMN_TYPE_WIDTH = 25              # Kolumna typu pliku (ikona)
COLUMN_FILENAME_WIDTH = 180         # Kolumna nazwy pliku
COLUMN_DURATION_WIDTH = 50          # Kolumna czasu trwania
COLUMN_PLAY_WIDTH = 35              # Kolumna przycisku play
COLUMN_DELETE_WIDTH = 30            # Kolumna przycisku usuwania

# Szerokość przewijalnej ramki w panelu "Wybrane"
SCROLLABLE_FRAME_WIDTH = 484        # Szerokość wewnętrznej ramki przewijalnej

# Maksymalne długości nazw plików (dla ellipsis)
MAX_FILENAME_LENGTH_SELECTED = 30   # W panelu "Wybrane"
MAX_FILENAME_LENGTH_STATUS = 25     # W panelach statusu