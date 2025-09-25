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
    Waliduje czas trwania plików pobranych z bazy danych (ze statusem 'selected').
    Aktualizuje ich czas trwania w bazie danych.
    Ta funkcja jest głównie używana w trybie CLI.

    Returns:
        list: Lista ścieżek do plików, które są dłuższe niż dozwolony limit.
    """
    long_files = []
    files_to_check = database.get_files_by_status('selected')

    if not files_to_check:
        print("Brak plików do walidacji.")
        return long_files

    for file_path in files_to_check:
        duration = get_file_duration(file_path)
        # Aktualizujemy czas trwania w bazie danych, aby nie obliczać go ponownie
        database.update_file_duration(file_path, duration)

        if duration > config.MAX_FILE_DURATION_SECONDS:
            long_files.append(os.path.basename(file_path))

    return long_files