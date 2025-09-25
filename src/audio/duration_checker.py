# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.
import subprocess
import json
import os
from src import config

def get_audio_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą ffprobe.

    Args:
        file_path (str): Ścieżka do pliku audio.

    Returns:
        float: Czas trwania pliku w sekundach lub None, jeśli wystąpił błąd.
    """
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        # Szukamy strumienia audio i pobieramy jego czas trwania
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio" and "duration" in stream:
                return float(stream["duration"])
        # Jeśli nie ma w strumieniach, sprawdzamy w formacie
        if "format" in data and "duration" in data["format"]:
            return float(data["format"]["duration"])
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, FileNotFoundError):
        return None

def validate_file_durations(max_duration=300):
    """
    Sprawdza, czy pliki na liście do przetworzenia nie przekraczają maksymalnej długości.

    Args:
        max_duration (int): Maksymalna dozwolona długość pliku w sekundach.

    Returns:
        list: Lista ścieżek do plików, które są za długie.
    """
    long_files = []
    with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            file_path = line.strip()
            duration = get_audio_duration(file_path)
            if duration is not None and duration > max_duration:
                long_files.append(os.path.basename(file_path))
    return long_files