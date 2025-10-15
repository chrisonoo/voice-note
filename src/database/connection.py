# Database connection management module

import sqlite3  # Standardowa biblioteka Pythona do obsługi baz danych SQLite.
import os  # Biblioteka do interakcji z systemem operacyjnym, np. operacje na plikach i folderach.
import functools  # Używane do tworzenia dekoratorów, które "owijają" inne funkcje.
import time  # Dodane dla optymalizacji wydajności
from datetime import datetime
from src import config  # Importujemy nasz plik konfiguracyjny.

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

@log_db_operation
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
