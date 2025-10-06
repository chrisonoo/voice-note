# -*- coding: utf-8 -*-

# Ten moduł odpowiada za przetwarzanie metadanych plików audio,
# w tym obliczanie czasu rozpoczęcia, zakończenia, trwania nagrania
# oraz przerw między kolejnymi nagraniami.

import os
from datetime import datetime, timedelta
from . import database, config
from .audio.duration_checker import get_file_duration

def _format_timedelta_to_hms(td: timedelta):
    """Formatuje obiekt timedelta do czytelnego formatu HH:MM:SS."""
    if not isinstance(td, timedelta):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def _format_timedelta_to_mss(td: timedelta):
    """Formatuje obiekt timedelta do czytelnego formatu MM:SS.ms."""
    if not isinstance(td, timedelta):
        return "00:00.000"
    total_seconds = td.total_seconds()
    minutes, seconds = divmod(total_seconds, 60)
    milliseconds = td.microseconds // 1000
    return f"{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"

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

        all_metadata_to_update.append({
            'id': file_info['id'],
            'start_datetime': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_ms': duration_ms,
            'end_datetime': end_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'previous_ms': previous_ms,
            'is_selected': is_selected
        })

    if all_metadata_to_update:
        database.update_all_metadata_bulk(all_metadata_to_update)
        print(f"Pomyślnie przetworzono i zaktualizowano metadane dla {len(all_metadata_to_update)} plików.")

    print("--- Zakończono centralne przetwarzanie metadanych ---")
    return long_files

def format_transcription_header(file_metadata):
    """
    Tworzy sformatowany nagłówek tekstowy na podstawie metadanych z bazy.
    """
    if not file_metadata or 'start_datetime' not in file_metadata or file_metadata['start_datetime'] is None:
        return ""

    start_dt = datetime.strptime(file_metadata['start_datetime'], '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(file_metadata['end_datetime'], '%Y-%m-%d %H:%M:%S.%f')
    duration_td = timedelta(milliseconds=file_metadata['duration_ms'])
    previous_td = timedelta(milliseconds=file_metadata['previous_ms'])

    # Formatujemy wartości do szablonu.
    start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_dt.strftime('%H:%M:%S.%f')[:-3]
    duration_str = _format_timedelta_to_mss(duration_td)
    previous_str = _format_timedelta_to_hms(previous_td)

    return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"