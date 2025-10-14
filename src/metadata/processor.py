# Metadata processing module

import os
from datetime import datetime, timedelta
from .formatter import _create_file_tag
from src import database, config
from src.audio.duration_checker import get_file_duration
from src.utils.error_handlers import with_error_handling, measure_performance

@with_error_handling("Przetwarzanie metadanych")
@measure_performance
def process_and_update_all_metadata(allow_long=False):
    """
    Centralna funkcja do przetwarzania metadanych.
    Wczytuje pliki bez metadanych, sortuje je w pamięci wg daty modyfikacji,
    oblicza wszystkie metadane (w tym flagę `is_selected`), zapisuje je masowo do bazy
    i zwraca listę plików, które przekraczają limit długości.
    """
    print("\n--- Rozpoczynam centralne przetwarzanie metadanych ---")

    files_to_process = database.get_files_needing_metadata()
    if not files_to_process:
        print("Brak nowych plików do przetworzenia metadanych.")
        return []

    try:
        files_with_mtime = []
        for file_row in files_to_process:
            mtime = os.path.getmtime(file_row['source_file_path'])
            files_with_mtime.append({**file_row, 'mtime': mtime})

        sorted_files = sorted(files_with_mtime, key=lambda x: x['mtime'])
    except OSError as e:
        print(f"BŁĄD: Nie można posortować plików, problem z dostępem do pliku: {e}")
        return []

    all_metadata_to_update = []
    long_files = []
    previous_end_datetime = None

    for file_info in sorted_files:
        start_dt = datetime.fromtimestamp(file_info['mtime'])
        duration_sec = get_file_duration(file_info['source_file_path'])
        duration_ms = int(duration_sec * 1000)
        end_dt = start_dt + timedelta(milliseconds=duration_ms)

        if previous_end_datetime:
            previous_ms = int((start_dt - previous_end_datetime).total_seconds() * 1000)
        else:
            previous_ms = 0

        previous_end_datetime = end_dt

        is_long = duration_sec > config.MAX_FILE_DURATION_SECONDS
        if is_long:
            long_files.append(os.path.basename(file_info['source_file_path']))

        is_selected = True if allow_long else not is_long

        # Tworzymy tag na podstawie metadanych
        tag = _create_file_tag(start_dt, end_dt, duration_ms, previous_ms)

        all_metadata_to_update.append({
            'id': file_info['id'],
            'start_datetime': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_ms': duration_ms,
            'end_datetime': end_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'previous_ms': previous_ms,
            'is_selected': is_selected,
            'tag': tag
        })

    if all_metadata_to_update:
        database.update_all_metadata_bulk(all_metadata_to_update)
        print(f"Pomyślnie przetworzono i zaktualizowano metadane dla {len(all_metadata_to_update)} plików.")

    print("--- Zakończono centralne przetwarzanie metadanych ---")
    return long_files
