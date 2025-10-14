# Ten moduł zawiera funkcje do sprawdzania długości (czasu trwania) plików audio.
# Wykorzystuje do tego celu bibliotekę PyAV do analizy metadanych strumieni audio.

import os  # Moduł do interakcji z systemem operacyjnym, np. do pobierania nazwy pliku ze ścieżki.
import av  # PyAV do analizy metadanych audio
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.

def get_file_duration(file_path):
    """
    Pobiera czas trwania pliku audio za pomocą PyAV z cachowaniem.

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
    Oblicza czas trwania pliku audio za pomocą PyAV (bez cachowania).
    """
    try:
        # Otwórz plik z PyAV
        container = av.open(file_path)

        # Znajdź strumień audio
        audio_stream = None
        for stream in container.streams:
            if stream.type == 'audio':
                audio_stream = stream
                break

        if audio_stream is None:
            print(f"Nie znaleziono strumienia audio w pliku {os.path.basename(file_path)}")
            container.close()
            return 0.0

        # Pobierz czas trwania z metadanych strumienia
        duration = float(audio_stream.duration * audio_stream.time_base)

        container.close()
        return duration

    except Exception as e:
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