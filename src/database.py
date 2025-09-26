import sqlite3
import os
import shutil
import functools
from . import config
from .audio.duration_checker import get_file_duration

def log_db_operation(func):
    """A decorator to log database operations if DATABASE_LOGGING is True."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not config.DATABASE_LOGGING:
            return func(*args, **kwargs)

        # Log the function call
        arg_repr = [repr(a) for a in args]
        kwarg_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(arg_repr + kwarg_repr)
        print(f"--- DB LOG: Calling {func.__name__}({signature})")

        # Execute the function
        try:
            result = func(*args, **kwargs)
            # Log the result
            print(f"--- DB LOG: {func.__name__} returned: {result!r}")
            return result
        except Exception as e:
            print(f"--- DB LOG: {func.__name__} raised an exception: {e!r}")
            raise
    return wrapper

def get_db_connection():
    """Nawiązuje połączenie z bazą danych."""
    # Upewnij się, że folder bazy danych istnieje
    os.makedirs(os.path.dirname(config.DATABASE_FILE), exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@log_db_operation
def initialize_database():
    """
    Inicjalizuje bazę danych. Jeśli baza danych lub tabela 'files' nie istnieje,
    tworzy nową, czystą strukturę. Jeśli tabela istnieje i zawiera dane,
    nie robi nic, aby zapobiec nadpisaniu.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Sprawdź, czy tabela 'files' istnieje
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    table_exists = cursor.fetchone()

    if table_exists:
        # Sprawdź, czy tabela 'files' ma jakiekolwiek dane
        cursor.execute("SELECT 1 FROM files LIMIT 1")
        has_data = cursor.fetchone()
        if has_data:
            print("Baza danych już istnieje i zawiera dane. Inicjalizacja pominięta.")
            conn.close()
            return

    # Jeśli tabela nie istnieje lub jest pusta, stwórz ją od nowa
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file_path TEXT NOT NULL UNIQUE,
        tmp_file_path TEXT,
        is_selected BOOLEAN NOT NULL DEFAULT 1,
        is_loaded BOOLEAN NOT NULL DEFAULT 0,
        is_processed BOOLEAN NOT NULL DEFAULT 0,
        transcription TEXT,
        duration_seconds REAL
    );
    """)

    conn.commit()
    conn.close()
    print(f"Baza danych została zainicjalizowana w: {config.DATABASE_FILE}")

@log_db_operation
def add_file(file_path):
    """
    Dodaje nowy plik do bazy danych, jeśli jeszcze nie istnieje.
    Automatycznie oblicza czas trwania i ustawia flagę 'is_selected'.
    """
    duration = get_file_duration(file_path)
    # Długie nagrania są domyślnie odznaczone
    is_selected = not (duration > config.MAX_FILE_DURATION_SECONDS)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO files (source_file_path, duration_seconds, is_selected)
            VALUES (?, ?, ?)
            """,
            (file_path, duration, is_selected)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Plik już istnieje w bazie, ignorujemy błąd
        pass
    finally:
        conn.close()

@log_db_operation
def update_file_duration(file_path, duration):
    """Aktualizuje czas trwania dla danego pliku."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE files SET duration_seconds = ? WHERE source_file_path = ?
    """, (duration, file_path))
    conn.commit()
    conn.close()

@log_db_operation
def update_file_durations_bulk(files_data):
    """Masowo aktualizuje czasy trwania dla listy plików."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # files_data to lista krotek [(path, duration), ...]
    update_data = [(duration, path) for path, duration in files_data]
    cursor.executemany(
        "UPDATE files SET duration_seconds = ? WHERE source_file_path = ?",
        update_data
    )
    conn.commit()
    conn.close()

@log_db_operation
def update_file_transcription(file_path, transcription_text):
    """Zapisuje transkrypcję dla pliku i oznacza go jako przetworzony."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE files
    SET transcription = ?, is_processed = 1
    WHERE source_file_path = ?
    """, (transcription_text, file_path))
    conn.commit()
    conn.close()

@log_db_operation
def set_file_selected(file_path, is_selected):
    """Ustawia flagę zaznaczenia dla pojedynczego pliku."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE files SET is_selected = ? WHERE source_file_path = ?
    """, (is_selected, file_path))
    conn.commit()
    conn.close()

@log_db_operation
def get_files_to_load():
    """Pobiera listę plików, które są zaznaczone i niezaładowane."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source_file_path FROM files WHERE is_selected = 1 AND is_loaded = 0 ORDER BY source_file_path")
    files = [row['source_file_path'] for row in cursor.fetchall()]
    conn.close()
    return files

@log_db_operation
def get_files_to_process():
    """Pobiera listę plików, które są załadowane i nieprzetworzone."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source_file_path FROM files WHERE is_loaded = 1 AND is_processed = 0 ORDER BY source_file_path")
    files = [row['source_file_path'] for row in cursor.fetchall()]
    conn.close()
    return files

@log_db_operation
def set_files_as_loaded(file_paths, tmp_file_paths):
    """Oznacza listę plików jako załadowane i zapisuje ich ścieżki tymczasowe."""
    conn = get_db_connection()
    cursor = conn.cursor()
    update_data = [
        (True, tmp_path, src_path)
        for src_path, tmp_path in zip(file_paths, tmp_file_paths)
    ]
    cursor.executemany(
        "UPDATE files SET is_loaded = ?, tmp_file_path = ? WHERE source_file_path = ?",
        update_data
    )
    conn.commit()
    conn.close()

@log_db_operation
def get_all_files():
    """Pobiera wszystkie pliki z bazy danych."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM files ORDER BY source_file_path").fetchall()
    conn.close()
    return rows

@log_db_operation
def clear_database_and_tmp_folder():
    """
    Usuwa cały folder tymczasowy (w tym bazę danych i pliki .wav),
    a następnie odtwarza pustą bazę danych.
    """
    if os.path.exists(config.TMP_DIR):
        shutil.rmtree(config.TMP_DIR)
        print(f"Folder tymczasowy usunięty: {config.TMP_DIR}")
    # Upewnij się, że folder tmp jest tworzony ponownie
    os.makedirs(config.TMP_DIR, exist_ok=True)
    initialize_database()

@log_db_operation
def unselect_all_files():
    """Odznacza wszystkie pliki w bazie danych."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET is_selected = 0")
    conn.commit()
    conn.close()

@log_db_operation
def delete_file(file_path):
    """
    Usuwa plik z bazy danych oraz fizycznie z dysku.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the temporary file path before deleting the record
    cursor.execute("SELECT tmp_file_path FROM files WHERE source_file_path = ?", (file_path,))
    result = cursor.fetchone()
    tmp_file_path = result['tmp_file_path'] if result else None

    # Delete from database
    cursor.execute("DELETE FROM files WHERE source_file_path = ?", (file_path,))
    conn.commit()
    conn.close()

    # Delete source file
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Usunięto plik źródłowy: {file_path}")
    except OSError as e:
        print(f"Błąd podczas usuwania pliku źródłowego {file_path}: {e}")

    # Delete temporary file
    if tmp_file_path:
        try:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                print(f"Usunięto plik tymczasowy: {tmp_file_path}")
        except OSError as e:
            print(f"Błąd podczas usuwania pliku tymczasowego {tmp_file_path}: {e}")