import os

# --- Ścieżki do katalogów ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC_DIR = os.path.join(BASE_DIR, 'rec')
INPUT_DIR = os.path.join(REC_DIR, 'input')
OUTPUT_DIR = os.path.join(REC_DIR, 'output')

# --- Ścieżki do plików stanu ---
# Pliki te pomagają śledzić postęp i wznowić pracę w razie błędu.
AUDIO_LIST_TO_ENCODE_FILE = os.path.join(REC_DIR, '1_audio_list_to_encode.txt')
AUDIO_LIST_TO_TRANSCRIBE_FILE = os.path.join(REC_DIR, '2_audio_list_to_transcribe.txt')
PROCESSING_LIST_FILE = os.path.join(REC_DIR, '3_processing_list.txt')
PROCESSED_LIST_FILE = os.path.join(REC_DIR, '4_processed_list.txt')
TRANSCRIPTIONS_FILE = os.path.join(REC_DIR, '5_transcriptions.txt')

# --- Parametry transkrypcji Whisper ---
WHISPER_API_RESPONSE_FORMAT = "json"
WHISPER_API_TEMPERATURE = 0
WHISPER_API_PROMPT = ""  # Możesz dodać tutaj tekst, aby poprawić jakość transkrypcji

# --- Ustawienia enkodowania audio ---
# Lista rozszerzeń plików audio do przetworzenia
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.wma']
# Parametry dla FFMPEG (1 kanał, próbkowanie 44100 Hz)
FFMPEG_PARAMS = '-ac 1 -ar 44100'