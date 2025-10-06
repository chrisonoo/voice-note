# Ten moduł zarządza wszystkimi operacjami na bazie danych SQLite.
# Baza danych przechowuje stan aplikacji, w tym listę plików, ich statusy
# (czy są zaznaczone, przetworzone) oraz wyniki transkrypcji.
# Dzięki temu aplikacja może być zamykana i otwierana bez utraty postępów.

import sqlite3  # Standardowa biblioteka Pythona do obsługi baz danych SQLite.
import os  # Biblioteka do interakcji z systemem operacyjnym, np. operacje na plikach i folderach.
import shutil  # Biblioteka do operacji na plikach wysokiego poziomu, np. usuwanie całych drzew folderów.
import functools  # Używane do tworzenia dekoratorów, które "owijają" inne funkcje.
import time  # Dodane dla optymalizacji wydajności
from datetime import datetime
from . import config  # Importujemy nasz plik konfiguracyjny, aby mieć dostęp do globalnych ustawień.
from .audio.duration_checker import get_file_duration  # Importujemy funkcję do sprawdzania długości plików audio.

# Singleton dla połączenia z bazą danych
_db_connection = None
_db_connection_lock = time.thread_time_ns()  # Prosty lock dla bezpieczeństwa wątkowego

def _format_row(row):
    """Formatuje obiekt sqlite3.Row do czytelnego ciągu znaków, np. 'id: 1, name: test'."""
    # Jeśli wiersz jest pusty (None), zwracamy informację.
    if not row:
        return "Brak wyniku"
    # Używamy "generator expression" do stworzenia par klucz:wartość dla każdego pola w wierszu
    # i łączymy je przecinkami w jeden string.
    return ", ".join(f"{key}: {row[key]}" for key in row.keys())

def log_db_operation(func):
    """Dekorator do logowania operacji na bazie danych, jeśli DATABASE_LOGGING ma wartość True."""
    # @functools.wraps(func) zachowuje metadane oryginalnej funkcji (np. jej nazwę), co jest dobrą praktyką.
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Sprawdzamy flagę w konfiguracji. Jeśli jest False, po prostu wywołujemy oryginalną funkcję bez logowania.
        if not config.DATABASE_LOGGING:
            return func(*args, **kwargs)

        # Przygotowujemy czytelną reprezentację argumentów, z którymi funkcja została wywołana.
        arg_repr = [repr(a) for a in args]
        kwarg_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(arg_repr + kwarg_repr)
        print(f"--- DB LOG: Wywołanie {func.__name__}({signature})")

        try:
            # Wywołujemy oryginalną funkcję i przechowujemy jej wynik.
            result = func(*args, **kwargs)
            # Sprawdzamy typ wyniku, aby go ładnie sformatować w logach.
            if isinstance(result, list) and all(isinstance(r, sqlite3.Row) for r in result):
                print(f"--- DB LOG: {func.__name__} zwróciła {len(result)} wierszy:")
                for row in result:
                    print(f"  - {_format_row(row)}")
            elif isinstance(result, sqlite3.Row):
                 print(f"--- DB LOG: {func.__name__} zwróciła: {_format_row(result)}")
            else:
                print(f"--- DB LOG: {func.__name__} zwróciła: {result!r}")
            return result
        except Exception as e:
            # Jeśli funkcja rzuci wyjątek, logujemy go.
            print(f"--- DB LOG: {func.__name__} rzuciła wyjątek: {e!r}")
            raise  # Rzucamy wyjątek dalej, aby nie zmieniać działania programu.
    return wrapper

def _execute_query(cursor, query, params=None, fetch=None):
    """
    Pomocnicza funkcja do wykonywania zapytań SQL, która integruje logowanie.

    Argumenty:
        cursor: Aktywny kursor bazy danych.
        query (str): Zapytanie SQL do wykonania.
        params (tuple, opcjonalnie): Parametry do zapytania, chroniące przed SQL Injection.
        fetch (str, opcjonalnie): Określa, czy pobrać jeden wynik ('one'), wszystkie ('all'), czy żaden.
    """
    # Logujemy zapytanie i parametry, jeśli logowanie jest włączone.
    if config.DATABASE_LOGGING:
        print(f"--- DB EXEC: Zapytanie: {query.strip()}")
        if params:
            print(f"--- DB EXEC: Parametry: {params}")

    # Wykonujemy zapytanie. Użycie `params` jest bezpieczniejsze niż formatowanie stringów.
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    # Zwracamy wyniki w zależności od wartości argumentu `fetch`.
    if fetch == 'one':
        return cursor.fetchone()
    if fetch == 'all':
        return cursor.fetchall()

def get_db_connection():
    """Nawiązuje połączenie z bazą danych i zwraca obiekt połączenia (singleton z optymalizacjami)."""
    global _db_connection

    if _db_connection is None:
        # Upewniamy się, że folder, w którym ma być baza danych, istnieje.
        os.makedirs(os.path.dirname(config.DATABASE_FILE), exist_ok=True)

        # Łączymy się z plikiem bazy danych zdefiniowanym w konfiguracji.
        _db_connection = sqlite3.connect(config.DATABASE_FILE, check_same_thread=False)

        # `row_factory = sqlite3.Row` sprawia, że wyniki zapytań będą dostępne jak słowniki (po nazwach kolumn),
        # co jest znacznie czytelniejsze niż dostęp po indeksach.
        _db_connection.row_factory = sqlite3.Row

        # Optymalizacje SQLite dla lepszej wydajności
        _db_connection.execute("PRAGMA synchronous = NORMAL")  # Zbalansowana synchronizacja
        _db_connection.execute("PRAGMA cache_size = -1000000")  # 1GB cache (ujemna wartość = KB)
        _db_connection.execute("PRAGMA temp_store = memory")   # Przechowuj temp tabele w pamięci
        _db_connection.execute("PRAGMA mmap_size = 268435456") # 256MB memory-mapped I/O
        _db_connection.execute("PRAGMA journal_mode = WAL")    # Write-Ahead Logging dla lepszej współbieżności
        _db_connection.execute("PRAGMA wal_autocheckpoint = 1000")  # Auto-checkpoint co 1000 stron

    return _db_connection

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
def get_files_to_load():
    """Pobiera listę ścieżek do plików, które są zaznaczone i nie zostały jeszcze wczytane/przekonwertowane."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_selected = 1 AND is_loaded = 0 ORDER BY start_datetime", fetch='all')
        # Zwracamy listę ścieżek, a nie całe obiekty wierszy.
        return [row['source_file_path'] for row in rows]

@log_db_operation
def get_files_to_process():
    """Pobiera listę ścieżek do plików, które zostały wczytane (przekonwertowane), ale nie mają jeszcze transkrypcji."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_loaded = 1 AND is_processed = 0 ORDER BY start_datetime", fetch='all')
        return [row['source_file_path'] for row in rows]

@log_db_operation
def set_files_as_loaded(file_paths, tmp_file_paths):
    """Oznacza listę plików jako wczytane (przekonwertowane) i zapisuje ścieżki do ich tymczasowych wersji .wav."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Przygotowujemy dane do masowej aktualizacji.
        update_data = list(zip([True]*len(file_paths), tmp_file_paths, file_paths))
        cursor.executemany(
            "UPDATE files SET is_loaded = ?, tmp_file_path = ? WHERE source_file_path = ?",
            update_data
        )
        conn.commit()

@log_db_operation
def get_all_files():
    """Pobiera wszystkie pliki z bazy danych, posortowane chronologicznie."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(cursor, "SELECT * FROM files ORDER BY start_datetime", fetch='all')

@log_db_operation
def get_files_needing_metadata():
    """Pobiera pliki, które nie mają jeszcze przetworzonych metadanych (start_datetime jest NULL)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(cursor, "SELECT id, source_file_path FROM files WHERE start_datetime IS NULL", fetch='all')

@log_db_operation
def update_all_metadata_bulk(metadata_list):
    """Masowo aktualizuje wszystkie obliczone metadane dla listy plików."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Przygotowujemy dane do masowej aktualizacji.
        update_data = [
            (
                item['start_datetime'],
                item['duration_ms'],
                item['end_datetime'],
                item['previous_ms'],
                item['is_selected'],
                item['tag'],
                item['id']
            ) for item in metadata_list
        ]
        cursor.executemany(
            """
            UPDATE files
            SET start_datetime = ?, duration_ms = ?, end_datetime = ?, previous_ms = ?, is_selected = ?, tag = ?
            WHERE id = ?
            """,
            update_data
        )
        conn.commit()

@log_db_operation
def get_file_metadata(source_file_path):
    """Pobiera metadane dla pojedynczego pliku."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(
            cursor,
            "SELECT tmp_file_path, start_datetime, end_datetime, duration_ms, previous_ms, transcription, tag FROM files WHERE source_file_path = ?",
            (source_file_path,),
            fetch='one'
        )

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
    "Czyści" stan aplikacji. Usuwa cały folder tymczasowy (włączając w to bazę danych i pliki .wav),
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

@log_db_operation
def delete_file(file_path):
    """
    Usuwa plik z bazy danych oraz (jeśli istnieją) jego fizyczne odpowiedniki z dysku
    (plik źródłowy i tymczasowy plik .wav).
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
def get_cached_duration(file_path):
    """Pobiera zcache'owaną długość pliku z bazy danych."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(
            cursor,
            "SELECT duration_ms FROM files WHERE source_file_path = ? AND duration_ms IS NOT NULL",
            (file_path,),
            fetch='one'
        )

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