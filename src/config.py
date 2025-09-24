# Ten plik służy jako centralne miejsce do zarządzania wszystkimi ustawieniami aplikacji.
# Dzięki temu, jeśli chcesz coś zmienić (np. ścieżkę do folderu), robisz to tylko tutaj,
# bez potrzeby grzebania w innych plikach.

import os

# --- ŚCIEŻKI DO KATALOGÓW ---

# `os.path.abspath(__file__)` zwraca pełną, absolutną ścieżkę do tego pliku (`config.py`).
# `os.path.dirname(...)` usuwa ostatni komponent ścieżki, dając nam ścieżkę do folderu,
# w którym znajduje się plik. Robimy to dwa razy, aby cofnąć się z `src/` do głównego
# katalogu projektu. To sprawia, że ścieżki są zawsze poprawne, niezależnie od tego,
# z jakiego miejsca na komputerze uruchomisz aplikację.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `os.path.join` to bezpieczny sposób łączenia ścieżek, który działa na różnych
# systemach operacyjnych (Windows, macOS, Linux).
REC_DIR = os.path.join(BASE_DIR, 'rec')
INPUT_DIR = os.path.join(REC_DIR, 'input')
OUTPUT_DIR = os.path.join(REC_DIR, 'output')


# --- ŚCIEŻKI DO PLIKÓW STANU ---
# Pliki te pomagają śledzić postęp i umożliwiają wznowienie pracy w razie błędu.
# Przechowują listy plików na różnych etapach przetwarzania.
AUDIO_LIST_TO_ENCODE_FILE = os.path.join(REC_DIR, '1_audio_list_to_encode.txt')
AUDIO_LIST_TO_TRANSCRIBE_FILE = os.path.join(REC_DIR, '2_audio_list_to_transcribe.txt')
PROCESSING_LIST_FILE = os.path.join(REC_DIR, '3_processing_list.txt')
PROCESSED_LIST_FILE = os.path.join(REC_DIR, '4_processed_list.txt')
TRANSCRIPTIONS_FILE = os.path.join(REC_DIR, '5_transcriptions.txt')


# --- PARAMETRY TRANSKRYPCJI WHISPER ---
# Tutaj możesz dostosować, jak API OpenAI ma przetwarzać Twoje pliki.

# Format odpowiedzi od API. "json" jest dobry do dalszego przetwarzania,
# "text" dałby czysty tekst.
WHISPER_API_RESPONSE_FORMAT = "json"

# "Temperatura" kontroluje "kreatywność" lub "losowość" modelu.
# Dla transkrypcji, gdzie chcemy jak najwierniejszego wyniku, 0 jest najlepszą wartością.
WHISPER_API_TEMPERATURE = 0

# "Prompt" to tekst, który możesz podać modelowi, aby "naprowadzić" go na
# odpowiedni kontekst, np. jeśli w nagraniach często padają specyficzne
# nazwy własne lub terminy techniczne.
WHISPER_API_PROMPT = ""


# --- USTAWIENIA ENKODOWANIA AUDIO ---

# Lista rozszerzeń plików, które aplikacja będzie wyszukiwać w folderze `input`.
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']

# Parametry dla FFMPEG używane podczas konwersji.
# `-ac 1` ustawia jeden kanał audio (mono).
# `-ar 44100` ustawia częstotliwość próbkowania na 44100 Hz.
# To standardowe, bezpieczne ustawienia dla API Whisper.
FFMPEG_PARAMS = '-ac 1 -ar 44100'