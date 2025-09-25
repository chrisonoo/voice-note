# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.

import os
import subprocess
import json
from src import config

def get_file_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą ffprobe.

    Args:
        file_path (str): Ścieżka do pliku audio.

    Returns:
        float: Czas trwania pliku w sekundach lub 0.0, jeśli wystąpi błąd.
    """
    # Polecenie ffprobe do uzyskania informacji o pliku w formacie JSON
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    try:
        # Uruchomienie polecenia
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # Parsowanie wyniku JSON
        data = json.loads(result.stdout)
        # Zwracanie czasu trwania z informacji o formacie
        return float(data['format']['duration'])
    except (subprocess.CalledProcessError, KeyError, FileNotFoundError) as e:
        # Obsługa błędów, np. gdy ffprobe nie jest zainstalowany lub plik jest uszkodzony
        print(f"Błąd podczas sprawdzania czasu trwania pliku {os.path.basename(file_path)}: {e}")
        return 0.0

def validate_file_durations():
    """
    Waliduje czas trwania plików z listy `AUDIO_LIST_TO_ENCODE_FILE`.
    Ta funkcja jest głównie używana w trybie CLI.

    Returns:
        list: Lista ścieżek do plików, które są dłuższe niż dozwolony limit.
    """
    long_files = []
    try:
        with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'r', encoding='utf-8') as f:
            files_to_check = [line.strip() for line in f.readlines()]

        for file_path in files_to_check:
            duration = get_file_duration(file_path)
            if duration > config.MAX_FILE_DURATION_SECONDS:
                long_files.append(os.path.basename(file_path))
    except FileNotFoundError:
        print("Plik z listą audio do sprawdzenia nie istnieje.")

    return long_files