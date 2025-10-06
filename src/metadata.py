# -*- coding: utf-8 -*-

# Ten moduł odpowiada za przetwarzanie metadanych plików audio,
# w tym obliczanie czasu rozpoczęcia, zakończenia, trwania nagrania
# oraz przerw między kolejnymi nagraniami.

import os
from datetime import datetime, timedelta
from . import database, config
from .audio.duration_checker import get_file_duration
from .utils.error_handlers import with_error_handling, measure_performance  # Dekoratory

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

def _create_file_tag(start_dt: datetime, end_dt: datetime, duration_ms: int, previous_ms: int):
    """
    Tworzy tag dla pliku na podstawie jego metadanych czasowych.
    Tag jest tworzony podczas przetwarzania metadanych, przed transkrypcją.
    """
    try:
        # Formatowanie dat i czasów
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_dt.strftime('%H:%M:%S.%f')[:-3]  # Bez daty, tylko czas

        # Czas trwania
        duration_td = timedelta(milliseconds=duration_ms)
        duration_str = _format_timedelta_to_mss(duration_td)

        # Czas od poprzedniego nagrania
        if previous_ms > 0:
            previous_td = timedelta(milliseconds=previous_ms)
            previous_str = _format_timedelta_to_hms(previous_td)
        else:
            previous_str = "00:00:00"

        return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"

    except Exception as e:
        print(f"Błąd podczas tworzenia tagu: {e}")
        return "[TAG_ERROR]"

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

def format_transcription_header(file_metadata):
    """
    Tworzy sformatowany nagłówek tekstowy na podstawie metadanych z bazy.
    Funkcja jest odporna na brakujące dane (NULL w bazie).
    Obsługuje zarówno słowniki jak i obiekty sqlite3.Row.
    """
    if not file_metadata:
        return ""

    # Definiujemy domyślne wartości na wypadek błędów lub braku danych.
    start_str = "N/A"
    end_str = "N/A"
    duration_str = "N/A"
    previous_str = "N/A"

    try:
        # Próbujemy sformatować datę rozpoczęcia.
        # Używamy bezpośredniego dostępu [] zamiast .get(), bo sqlite3.Row nie ma metody .get()
        try:
            start_dt_str = file_metadata['start_datetime']
        except (KeyError, IndexError):
            start_dt_str = None
            
        if start_dt_str:
            start_dt = datetime.strptime(start_dt_str, '%Y-%m-%d %H:%M:%S')
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Próbujemy sformatować datę zakończenia.
        try:
            end_dt_str = file_metadata['end_datetime']
        except (KeyError, IndexError):
            end_dt_str = None
            
        if end_dt_str:
            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d %H:%M:%S.%f')
            end_str = end_dt.strftime('%H:%M:%S.%f')[:-3]

        # Próbujemy sformatować czas trwania.
        try:
            duration_ms = file_metadata['duration_ms']
        except (KeyError, IndexError):
            duration_ms = None
            
        if duration_ms is not None:
            duration_td = timedelta(milliseconds=duration_ms)
            duration_str = _format_timedelta_to_mss(duration_td)

        # Próbujemy sformatować przerwę od poprzedniego.
        try:
            previous_ms = file_metadata['previous_ms']
        except (KeyError, IndexError):
            previous_ms = None
            
        if previous_ms is not None:
            previous_td = timedelta(milliseconds=previous_ms)
            previous_str = _format_timedelta_to_hms(previous_td)

    except (TypeError, ValueError) as e:
        # W przypadku błędu parsowania, logujemy go, ale nie przerywamy działania.
        print(f"    OSTRZEŻENIE: Błąd podczas formatowania nagłówka transkrypcji: {e}")
        # Wartości pozostaną jako "N/A".

    # Zwracamy pusty string tylko jeśli brakuje kluczowej informacji o starcie.
    if start_str == "N/A":
        return ""

    return f"[START: {start_str} | END: {end_str} | DURATION: {duration_str} | PREVIOUS: {previous_str}]"