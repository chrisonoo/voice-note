# Database operations module - CRUD operations

import os
import sqlite3

from .connection import execute_query, get_db_connection, log_db_operation  # type: ignore


@log_db_operation
def add_file(file_path: str) -> None:
    """
    Dodaje nowy plik do bazy danych, jeśli jeszcze nie istnieje.
    Na tym etapie zapisujemy tylko ścieżkę, reszta metadanych zostanie
    obliczona w osobnym kroku.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Próbujemy wstawić nowy wiersz do tabeli.
            execute_query(cursor, "INSERT INTO files (source_file_path) VALUES (?)", (file_path,))
            conn.commit()
    except sqlite3.IntegrityError:
        # Jeśli plik już istnieje (dzięki ograniczeniu UNIQUE na kolumnie `source_file_path`),
        # baza rzuci błąd `IntegrityError`. My go przechwytujemy i ignorujemy, bo to oczekiwane zachowanie.
        pass
    except Exception as e:
        # Przechwytujemy inne potencjalne błędy.
        print(f"Błąd podczas dodawania pliku {file_path} do bazy: {e}")


@log_db_operation
def update_file_transcription(file_path: str, transcription_text: str) -> None:
    """Zapisuje transkrypcję dla pliku i oznacza go jako przetworzony."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        execute_query(
            cursor,
            "UPDATE files SET transcription = ?, is_processed = 1 WHERE source_file_path = ?",
            (transcription_text, file_path),
        )
        conn.commit()


@log_db_operation
def set_file_selected(file_path: str, is_selected: bool) -> None:
    """Ustawia flagę zaznaczenia (checkbox w GUI) dla pojedynczego pliku."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        execute_query(
            cursor,
            "UPDATE files SET is_selected = ? WHERE source_file_path = ?",
            (is_selected, file_path),
        )
        conn.commit()


@log_db_operation
def delete_file(file_path: str) -> None:
    """
    Usuwa plik z bazy danych oraz (jeśli istnieją) jego fizyczne odpowiedniki z dysku
    (plik źródłowy i tymczasowy przetworzony plik audio).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Najpierw pobieramy ścieżkę do pliku tymczasowego, zanim usuniemy wiersz z bazy.
        result = execute_query(
            cursor,
            "SELECT tmp_file_path FROM files WHERE source_file_path = ?",
            (file_path,),
            fetch="one",
        )
        tmp_file_path = result["tmp_file_path"] if result else None  # type: ignore

        # Usuwamy wiersz z bazy danych.
        execute_query(cursor, "DELETE FROM files WHERE source_file_path = ?", (file_path,))
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
        tmp_path_str = str(tmp_file_path)  # type: ignore
        try:
            if os.path.exists(tmp_path_str):
                os.remove(tmp_path_str)
                print(f"Usunięto plik tymczasowy: {tmp_path_str}")
        except OSError as e:
            print(f"Błąd podczas usuwania pliku tymczasowego {tmp_path_str}: {e}")


@log_db_operation
def cache_file_duration(file_path: str, duration_seconds: float) -> None:
    """Zapisuje obliczoną długość pliku w cache'u bazy danych."""
    duration_ms = int(duration_seconds * 1000)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        execute_query(
            cursor,
            "UPDATE files SET duration_ms = ? WHERE source_file_path = ?",
            (duration_ms, file_path),
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
def add_file_chunk(original_path: str, chunk_path: str, chunk_index: int) -> None:
    """
    Dodaje chunk jako osobny wpis w bazie danych, powiązany z plikiem rodzicielskim.

    Argumenty:
        original_path (str): Ścieżka do oryginalnego pliku
        chunk_path (str): Ścieżka do pliku chunk
        chunk_index (int): Numer części (1, 2, 3, ...)
    """
    try:
        # Oblicz duration_ms dla chunk'a
        from src.utils.audio.duration_checker import get_file_duration

        duration_sec = get_file_duration(chunk_path)
        duration_ms = int(duration_sec * 1000) if duration_sec > 0 else 0

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Dodajemy chunk jako nowy wpis w bazie z obliczoną długością
            execute_query(
                cursor,
                """INSERT INTO files
                   (source_file_path, tmp_file_path, parent_file_path, chunk_index, duration_ms, is_selected, is_loaded)
                   VALUES (?, ?, ?, ?, ?, 1, 1)""",
                (chunk_path, chunk_path, original_path, chunk_index, duration_ms),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # Jeśli chunk już istnieje, ignorujemy błąd
        pass
    except Exception as e:
        print(f"Błąd podczas dodawania chunk {chunk_index} dla pliku {original_path}: {e}")


@log_db_operation
def validate_file_access(file_path: str) -> tuple[bool, str | None]:
    """Sprawdza dostępność pliku przed przetworzeniem."""
    if not os.path.exists(file_path):
        return False, "Plik nie istnieje"

    try:
        # Sprawdź czy plik nie jest uszkodzony - czytaj pierwsze 1KB
        with open(file_path, "rb") as f:
            f.read(1024)
        return True, None
    except OSError as e:
        return False, f"Błąd dostępu do pliku: {e}"
