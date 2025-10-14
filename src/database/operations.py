# Database operations module - CRUD operations

import sqlite3
import os
from .connection import get_db_connection, _execute_query, log_db_operation

@log_db_operation
def add_file(file_path):
    """
    Dodaje nowy plik do bazy danych, jeśli jeszcze nie istnieje.
    Na tym etapie zapisujemy tylko ścieżkę, reszta metadanych zostanie
    obliczona w osobnym kroku.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Próbujemy wstawić nowy wiersz do tabeli.
            _execute_query(
                cursor,
                "INSERT INTO files (source_file_path) VALUES (?)",
                (file_path,)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Jeśli plik już istnieje (dzięki ograniczeniu UNIQUE na kolumnie `source_file_path`),
        # baza rzuci błąd `IntegrityError`. My go przechwytujemy i ignorujemy, bo to oczekiwane zachowanie.
        pass
    except Exception as e:
        # Przechwytujemy inne potencjalne błędy.
        print(f"Błąd podczas dodawania pliku {file_path} do bazy: {e}")

@log_db_operation
def update_file_transcription(file_path, transcription_text):
    """Zapisuje transkrypcję dla pliku i oznacza go jako przetworzony."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "UPDATE files SET transcription = ?, is_processed = 1 WHERE source_file_path = ?",
            (transcription_text, file_path)
        )
        conn.commit()

@log_db_operation
def set_file_selected(file_path, is_selected):
    """Ustawia flagę zaznaczenia (checkbox w GUI) dla pojedynczego pliku."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "UPDATE files SET is_selected = ? WHERE source_file_path = ?",
            (is_selected, file_path)
        )
        conn.commit()

@log_db_operation
def delete_file(file_path):
    """
    Usuwa plik z bazy danych oraz (jeśli istnieją) jego fizyczne odpowiedniki z dysku
    (plik źródłowy i tymczasowy przetworzony plik audio).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Najpierw pobieramy ścieżkę do pliku tymczasowego, zanim usuniemy wiersz z bazy.
        result = _execute_query(cursor, "SELECT tmp_file_path FROM files WHERE source_file_path = ?", (file_path,), fetch='one')
        tmp_file_path = result['tmp_file_path'] if result else None

        # Usuwamy wiersz z bazy danych.
        _execute_query(cursor, "DELETE FROM files WHERE source_file_path = ?", (file_path,))
        conn.commit()

    # Próbujemy usunąć plik źródłowy.
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Usunięto plik źródłowy: {file_path}")
    except OSError as e:
        print(f"Błąd podczas usuwania pliku źródłowego {file_path}: {e}")

    # Jeśli istniał plik tymczasowy, również próbujemy go usunąć.
    if tmp_file_path:
        try:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                print(f"Usunięto plik tymczasowy: {tmp_file_path}")
        except OSError as e:
            print(f"Błąd podczas usuwania pliku tymczasowego {tmp_file_path}: {e}")

@log_db_operation
def cache_file_duration(file_path, duration_seconds):
    """Zapisuje obliczoną długość pliku w cache'u bazy danych."""
    duration_ms = int(duration_seconds * 1000)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "UPDATE files SET duration_ms = ? WHERE source_file_path = ?",
            (duration_ms, file_path)
        )
        conn.commit()

@log_db_operation
def optimize_database():
    """Optymalizuje bazę danych - uruchamia VACUUM i ANALYZE."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        print("Optymalizacja bazy danych...")
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()
    print("Optymalizacja bazy danych zakończona.")

@log_db_operation
def validate_file_access(file_path):
    """Sprawdza dostępność pliku przed przetworzeniem."""
    if not os.path.exists(file_path):
        return False, "Plik nie istnieje"

    try:
        # Sprawdź czy plik nie jest uszkodzony - czytaj pierwsze 1KB
        with open(file_path, 'rb') as f:
            f.read(1024)
        return True, None
    except (OSError, IOError) as e:
        return False, f"Błąd dostępu do pliku: {e}"
