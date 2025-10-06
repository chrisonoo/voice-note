# -*- coding: utf-8 -*-

# Ten moduł odpowiada za przetwarzanie metadanych plików audio,
# w tym obliczanie czasu rozpoczęcia, zakończenia, trwania nagrania
# oraz przerw między kolejnymi nagraniami.

import os
import re
from datetime import datetime, timedelta
from . import database

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


def process_files_metadata():
    """
    Uzupełnia metadane plików (czas zakończenia, przerwy).
    Pobiera wszystkie pliki z bazy, sortuje je chronologicznie,
    oblicza brakujące metadane i zapisuje je z powrotem do bazy.
    """
    print("\n--- Rozpoczynam uzupełnianie metadanych plików ---")

    # Pobieramy wszystkie pliki z bazy danych, posortowane chronologicznie.
    files = database.get_all_files_for_metadata()
    if not files:
        print("Brak plików do przetworzenia.")
        return

    # Inicjalizujemy zmienną przechowującą czas zakończenia poprzedniego pliku.
    previous_end_datetime = None
    metadata_to_update = []

    # Przetwarzamy pliki w pętli.
    for file_data in files:
        # start_datetime jest już w bazie, parsujemy go do obiektu datetime.
        try:
            start_datetime = datetime.strptime(file_data['start_datetime'], '%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            print(f"    OSTRZEŻENIE: Nieprawidłowy format daty dla pliku: {file_data['source_file_path']}. Pomijanie.")
            continue

        # Czas trwania jest już w bazie (w milisekundach).
        duration_ms = file_data['duration_ms']
        duration_td = timedelta(milliseconds=duration_ms)

        # Obliczamy czas zakończenia.
        end_datetime = start_datetime + duration_td

        # Obliczamy przerwę od poprzedniego nagrania.
        if previous_end_datetime:
            # Różnica między startem bieżącego a końcem poprzedniego.
            previous_td = start_datetime - previous_end_datetime
            previous_ms = int(previous_td.total_seconds() * 1000)
        else:
            # Dla pierwszego pliku przerwa wynosi 0.
            previous_td = timedelta(seconds=0)
            previous_ms = 0

        # Przechowujemy czas zakończenia bieżącego pliku do następnej iteracji.
        previous_end_datetime = end_datetime

        # Przygotowujemy dane do aktualizacji w bazie.
        metadata_to_update.append({
            'id': file_data['id'],
            'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'previous_ms': previous_ms,
        })

    # Po przetworzeniu wszystkich plików, wykonujemy masową aktualizację w bazie danych.
    if metadata_to_update:
        database.update_files_metadata_bulk(metadata_to_update)
        print(f"Zaktualizowano metadane dla {len(metadata_to_update)} plików.")

    print("--- Zakończono przetwarzanie metadanych ---")

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
    previous_str = _format_timedelta_to_hms(previous_td) # Format HH:MM:SS

    return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"