# Ten moduł zarządza wszystkimi operacjami na bazie danych SQLite.
# Baza danych przechowuje stan aplikacji, w tym listę plików, ich statusy
# (czy są zaznaczone, przetworzone) oraz wyniki transkrypcji.
# Dzięki temu aplikacja może być zamykana i otwierana bez utraty postępów.

import sqlite3  # Standardowa biblioteka Pythona do obsługi baz danych SQLite.
import os  # Biblioteka do interakcji z systemem operacyjnym, np. operacje na plikach i folderach.
import shutil  # Biblioteka do operacji na plikach wysokiego poziomu, np. usuwanie całych drzew folderów.
import functools  # Używane do tworzenia dekoratorów, które "owijają" inne funkcje.
from . import config  # Importujemy nasz plik konfiguracyjny, aby mieć dostęp do globalnych ustawień.
from .audio.duration_checker import get_file_duration  # Importujemy funkcję do sprawdzania długości plików audio.

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
    """Nawiązuje połączenie z bazą danych i zwraca obiekt połączenia."""
    # Upewniamy się, że folder, w którym ma być baza danych, istnieje.
    # `exist_ok=True` sprawia, że funkcja nie rzuci błędu, jeśli folder już istnieje.
    os.makedirs(os.path.dirname(config.DATABASE_FILE), exist_ok=True)
    # Łączymy się z plikiem bazy danych zdefiniowanym w konfiguracji.
    conn = sqlite3.connect(config.DATABASE_FILE)
    # `row_factory = sqlite3.Row` sprawia, że wyniki zapytań będą dostępne jak słowniki (po nazwach kolumn),
    # co jest znacznie czytelniejsze niż dostęp po indeksach.
    conn.row_factory = sqlite3.Row
    return conn

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
            transcription TEXT,
            start_datetime TEXT,
            end_datetime TEXT,
            duration_ms INTEGER,
            previous_ms INTEGER
        );
        """)
        # `conn.commit()` zapisuje wszystkie zmiany wykonane w transakcji.
        conn.commit()
    print(f"Baza danych została zainicjalizowana w: {config.DATABASE_FILE}")

@log_db_operation
def add_file(file_path):
    """
    Dodaje nowy plik do bazy danych, jeśli jeszcze nie istnieje.
    Automatycznie oblicza czas trwania i na tej podstawie ustawia flagę 'is_selected'.
    """
    # Pobieramy czas trwania pliku w sekundach.
    duration_sec = get_file_duration(file_path)
    duration_ms = int(duration_sec * 1000)
    # Plik jest domyślnie odznaczony, jeśli jest za długi.
    is_selected = not (duration_sec > config.MAX_FILE_DURATION_SECONDS)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Próbujemy wstawić nowy wiersz do tabeli.
            # Używamy `?` jako placeholderów na wartości, co jest bezpieczną praktyką.
            _execute_query(
                cursor,
                "INSERT INTO files (source_file_path, duration_ms, is_selected) VALUES (?, ?, ?)",
                (file_path, duration_ms, is_selected)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Jeśli plik już istnieje (dzięki ograniczeniu UNIQUE na kolumnie `source_file_path`),
            # baza rzuci błąd `IntegrityError`. My go przechwytujemy i ignorujemy, bo to oczekiwane zachowanie.
            pass


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
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_selected = 1 AND is_loaded = 0 ORDER BY source_file_path", fetch='all')
        # Zwracamy listę ścieżek, a nie całe obiekty wierszy.
        return [row['source_file_path'] for row in rows]

@log_db_operation
def get_files_to_process():
    """Pobiera listę ścieżek do plików, które zostały wczytane (przekonwertowane), ale nie mają jeszcze transkrypcji."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_loaded = 1 AND is_processed = 0 ORDER BY source_file_path", fetch='all')
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
    """Pobiera wszystkie pliki z bazy danych, posortowane alfabetycznie."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(cursor, "SELECT * FROM files ORDER BY source_file_path", fetch='all')

@log_db_operation
def get_all_files_for_metadata():
    """Pobiera wszystkie pliki z bazy danych, posortowane alfabetycznie, na potrzeby przetwarzania metadanych."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Zwracamy tylko te kolumny, które są potrzebne do obliczeń metadanych.
        return _execute_query(cursor, "SELECT id, source_file_path, duration_ms FROM files ORDER BY source_file_path", fetch='all')

@log_db_operation
def update_files_metadata_bulk(metadata_list):
    """Masowo aktualizuje metadane dla listy plików."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Przygotowujemy dane do masowej aktualizacji.
        update_data = [
            (
                item['start_datetime'],
                item['end_datetime'],
                item['duration_ms'],
                item['previous_ms'],
                item['id']
            ) for item in metadata_list
        ]
        cursor.executemany(
            """
            UPDATE files
            SET start_datetime = ?, end_datetime = ?, duration_ms = ?, previous_ms = ?
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
            "SELECT tmp_file_path, start_datetime, end_datetime, duration_ms, previous_ms, transcription FROM files WHERE source_file_path = ?",
            (source_file_path,),
            fetch='one'
        )

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