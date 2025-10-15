# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.
# Wykorzystuje do tego celu zewnętrzne narzędzie `ffprobe`, które jest częścią pakietu FFMPEG.

import os  # Moduł do interakcji z systemem operacyjnym, np. do pobierania nazwy pliku ze ścieżki.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym `ffprobe`.
import json  # Moduł do pracy z formatem danych JSON, w którym `ffprobe` zwraca wyniki.
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.

def get_file_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą narzędzia ffprobe z cachowaniem.

    Najpierw sprawdza cache w bazie danych, jeśli nie ma - oblicza i zapisuje.

    Argumenty:
        file_path (str): Ścieżka do pliku audio, którego czas trwania ma być sprawdzony.

    Zwraca:
        float: Czas trwania pliku w sekundach. Jeśli wystąpi błąd, zwraca 0.0.
    """
    from src import database

    # Najpierw sprawdź cache w bazie danych
    cached_result = database.get_cached_duration(file_path)
    if cached_result:
        return cached_result['duration_ms'] / 1000.0

    # Jeśli nie ma w cache, oblicz duration
    duration_sec = _calculate_file_duration(file_path)

    # Zapisz w cache jeśli się udało obliczyć
    if duration_sec > 0:
        database.cache_file_duration(file_path, duration_sec)

    return duration_sec

def _calculate_file_duration(file_path):
    """
    Oblicza czas trwania pliku audio za pomocą ffprobe (bez cachowania).
    """
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Sprawdzanie długości pliku {os.path.basename(file_path)} przekroczyło limit czasu")
        return 0.0
    except Exception as e:
        print(f"Błąd podczas sprawdzania czasu trwania pliku {os.path.basename(file_path)}: {e}")
        return 0.0
