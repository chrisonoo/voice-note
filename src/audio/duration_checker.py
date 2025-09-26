# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.

import os
import subprocess
import json
from src import config, database

def get_file_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą ffprobe.

    Args:
        file_path (str): Ścieżka do pliku audio.

    Returns:
        float: Czas trwania pliku w sekundach lub 0.0, jeśli wystąpi błąd.
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
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except Exception as e:
        print(f"Błąd podczas sprawdzania czasu trwania pliku {os.path.basename(file_path)}: {e}")
        return 0.0

def validate_file_durations():
    """
    Waliduje czas trwania nowo dodanych plików (tych bez zapisanego czasu trwania).
    Aktualizuje ich czas trwania w bazie danych.
    Używane głównie w trybie CLI.

    Returns:
        list: Lista nazw plików, które są dłuższe niż dozwolony limit.
    """
    long_files = []
    all_files = database.get_all_files()

    # Sprawdzamy tylko pliki, które nie mają jeszcze obliczonego czasu trwania
    files_to_check = [row for row in all_files if row['duration_seconds'] is None]

    if not files_to_check:
        print("Brak nowych plików do walidacji czasu trwania.")
        return long_files

    for file_row in files_to_check:
        file_path = file_row['source_file_path']
        duration = get_file_duration(file_path)

        database.update_file_duration(file_path, duration)

        if duration > config.MAX_FILE_DURATION_SECONDS:
            long_files.append(os.path.basename(file_path))

    return long_files