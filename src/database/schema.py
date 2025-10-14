# Database schema management module

import sqlite3
import os
import shutil
from .connection import get_db_connection, _execute_query, log_db_operation
from src import config

@log_db_operation
def initialize_database():
    """
    Inicjalizuje bazę danych. Tworzy nową, czystą strukturę, jeśli baza lub tabela 'files' nie istnieje.
    Jeśli tabela istnieje i zawiera dane, nie robi nic, aby zapobiec ich utracie.
    """
    # `with` zapewnia, że połączenie z bazą danych zostanie automatycznie zamknięte po zakończeniu bloku.
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Sprawdzamy w specjalnej tabeli `sqlite_master`, czy nasza tabela `files` już istnieje.
        table_exists = _execute_query(cursor, "SELECT name FROM sqlite_master WHERE type='table' AND name='files'", fetch='one')

        # Jeśli tabela istnieje, sprawdzamy, czy zawiera jakiekolwiek dane.
        if table_exists:
            has_data = _execute_query(cursor, "SELECT 1 FROM files LIMIT 1", fetch='one')
            if has_data:
                print("Baza danych już istnieje i zawiera dane. Inicjalizacja pominięta.")
                return

        # Tworzymy tabelę `files`, jeśli nie istnieje.
        # `IF NOT EXISTS` zapobiega błędowi, gdyby tabela już istniała.
        # Definiujemy kolumny, ich typy oraz ograniczenia (np. NOT NULL, UNIQUE).
        _execute_query(cursor, """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file_path TEXT NOT NULL UNIQUE,
            tmp_file_path TEXT,
            is_selected BOOLEAN NOT NULL DEFAULT 1,
            is_loaded BOOLEAN NOT NULL DEFAULT 0,
            is_processed BOOLEAN NOT NULL DEFAULT 0,
            tag TEXT,
            transcription TEXT,
            start_datetime TEXT,
            end_datetime TEXT,
            duration_ms INTEGER,
            previous_ms INTEGER
        );
        """)
        # Dodajemy indeksy dla lepszej wydajności zapytań
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_selected_loaded ON files(is_selected, is_loaded)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_loaded_processed ON files(is_loaded, is_processed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_start_datetime ON files(start_datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_source_path ON files(source_file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_duration_ms ON files(duration_ms)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_tag ON files(tag)")

        # `conn.commit()` zapisuje wszystkie zmiany wykonane w transakcji.
        conn.commit()
    print(f"Baza danych została zainicjalizowana w: {config.DATABASE_FILE}")

@log_db_operation
def ensure_files_table_exists():
    """
    Sprawdza czy tabela files istnieje i jeśli nie - tworzy ją.
    Ta funkcja powinna być wywoływana przy wyborze plików.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Sprawdzamy czy tabela files istnieje
        table_exists = _execute_query(cursor, "SELECT name FROM sqlite_master WHERE type='table' AND name='files'", fetch='one')

        if not table_exists:
            # Tworzymy tabelę files jeśli nie istnieje
            cursor.execute("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file_path TEXT NOT NULL UNIQUE,
                tmp_file_path TEXT,
                is_selected BOOLEAN NOT NULL DEFAULT 1,
                is_loaded BOOLEAN NOT NULL DEFAULT 0,
                is_processed BOOLEAN NOT NULL DEFAULT 0,
                tag TEXT,
                transcription TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                duration_ms INTEGER,
                previous_ms INTEGER
            );
            """)

            # Dodajemy indeksy dla lepszej wydajności zapytań
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_selected_loaded ON files(is_selected, is_loaded)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_loaded_processed ON files(is_loaded, is_processed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_start_datetime ON files(start_datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_source_path ON files(source_file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_duration_ms ON files(duration_ms)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_tag ON files(tag)")

            conn.commit()
            print("Tabela 'files' została utworzona.")

@log_db_operation
def reset_files_table():
    """
    Resetuje aplikację do stanu początkowego przez usunięcie tabeli files
    i wyczyszczenie plików audio z folderu tymczasowego.
    Baza danych nie jest usuwana, tylko tabela files jest dropowana i tworzona ponownie.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Usuwamy tabelę files jeśli istnieje
        cursor.execute("DROP TABLE IF EXISTS files")
        print("Tabela 'files' została usunięta.")

        # Tworzymy pustą tabelę files
        cursor.execute("""
        CREATE TABLE files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file_path TEXT NOT NULL UNIQUE,
            tmp_file_path TEXT,
            is_selected BOOLEAN NOT NULL DEFAULT 1,
            is_loaded BOOLEAN NOT NULL DEFAULT 0,
            is_processed BOOLEAN NOT NULL DEFAULT 0,
            tag TEXT,
            transcription TEXT,
            start_datetime TEXT,
            end_datetime TEXT,
            duration_ms INTEGER,
            previous_ms INTEGER
        );
        """)

        # Dodajemy indeksy dla lepszej wydajności zapytań
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_selected_loaded ON files(is_selected, is_loaded)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_loaded_processed ON files(is_loaded, is_processed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_start_datetime ON files(start_datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_source_path ON files(source_file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_duration_ms ON files(duration_ms)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_tag ON files(tag)")

        conn.commit()
        print("Tabela 'files' została utworzona ponownie.")

    # Czyścimy pliki audio z folderu tymczasowego
    audio_dir = os.path.join(config.TMP_DIR, "audio")
    if os.path.exists(audio_dir):
        for file_name in os.listdir(audio_dir):
            file_path = os.path.join(audio_dir, file_name)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Usunięto plik audio: {file_path}")
            except OSError as e:
                print(f"Błąd podczas usuwania pliku {file_path}: {e}")

    print("Reset tabeli files zakończony.")

@log_db_operation
def clear_database_and_tmp_folder():
    """
    "Czyści" stan aplikacji. Usuwa cały folder tymczasowy (włączając w to bazę danych i przetworzone pliki audio),
    a następnie tworzy na nowo pustą strukturę.
    """
    # Sprawdzamy, czy folder tymczasowy istnieje.
    if os.path.exists(config.TMP_DIR):
        # `shutil.rmtree` usuwa folder wraz z całą jego zawartością.
        shutil.rmtree(config.TMP_DIR)
        print(f"Folder tymczasowy usunięty: {config.TMP_DIR}")
    # Tworzymy pusty folder `tmp`.
    os.makedirs(config.TMP_DIR, exist_ok=True)
    # Inicjalizujemy bazę danych od zera.
    initialize_database()
