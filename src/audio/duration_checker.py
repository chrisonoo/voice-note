# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.
# Wykorzystuje do tego celu zewnętrzne narzędzie `ffprobe`, które jest częścią pakietu FFMPEG.

import os  # Moduł do interakcji z systemem operacyjnym, np. do pobierania nazwy pliku ze ścieżki.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym `ffprobe`.
import json  # Moduł do pracy z formatem danych JSON, w którym `ffprobe` zwraca wyniki.
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.

def get_file_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą narzędzia ffprobe.

    Argumenty:
        file_path (str): Ścieżka do pliku audio, którego czas trwania ma być sprawdzony.

    Zwraca:
        float: Czas trwania pliku w sekundach. Jeśli wystąpi błąd, zwraca 0.0.
    """
    # Budujemy komendę `ffprobe`, która zostanie wykonana w terminalu.
    # `ffprobe -v quiet -print_format json -show_format -show_streams {plik}`
    # -v quiet: Wyłącza logowanie informacyjne ffprobe, aby nie "zaśmiecać" wyjścia.
    # -print_format json: Nakazuje ffprobe zwrócić wynik w formacie JSON, który jest łatwy do przetworzenia w Pythonie.
    # -show_format: Dołącza do wyniku ogólne informacje o formacie pliku (w tym czas trwania).
    # -show_streams: Dołącza informacje o poszczególnych strumieniach (audio, wideo) w pliku.
    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    try:
        # Uruchamiamy komendę `ffprobe`.
        # `capture_output=True`: Przechwytuje standardowe wyjście, gdzie znajdą się dane JSON.
        # `text=True`: Dekoduje przechwycone wyjście jako tekst.
        # `check=True`: Rzuci wyjątkiem, jeśli ffprobe zwróci błąd.
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # `json.loads` parsuje tekst w formacie JSON na słownik Pythona.
        data = json.loads(result.stdout)
        # Czas trwania całego pliku znajduje się w kluczu 'duration' w sekcji 'format'.
        # Konwertujemy go na typ float (liczba zmiennoprzecinkowa).
        return float(data['format']['duration'])
    except Exception as e:
        # Jeśli wystąpi jakikolwiek błąd (np. plik nie istnieje, nie jest plikiem multimedialnym, ffprobe nie jest zainstalowany),
        # łapiemy wyjątek, drukujemy komunikat i zwracamy bezpieczną wartość 0.0.
        print(f"Błąd podczas sprawdzania czasu trwania pliku {os.path.basename(file_path)}: {e}")
        return 0.0

def validate_file_durations():
    """
    Sprawdza, czy którykolwiek z plików w bazie danych przekracza dozwolony limit czasu trwania.
    Funkcja używana jest głównie w trybie wiersza poleceń (CLI).

    Zwraca:
        list: Lista samych nazw plików (bez ścieżek), które są dłuższe niż dozwolony limit.
    """
    long_files = []
    all_files = database.get_all_files()

    if not all_files:
        return long_files

    # Limit czasu trwania w milisekundach
    max_duration_ms = config.MAX_FILE_DURATION_SECONDS * 1000

    for file_row in all_files:
        # Sprawdzamy, czy czas trwania przekracza limit.
        # duration_ms może być None, jeśli coś poszło nie tak przy dodawaniu pliku
        if file_row['duration_ms'] is not None and file_row['duration_ms'] > max_duration_ms:
            long_files.append(os.path.basename(file_row['source_file_path']))

    return long_files