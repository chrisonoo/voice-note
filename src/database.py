import sqlite3
import os
import shutil
import functools
from . import config
from .audio.duration_checker import get_file_duration

def _format_row(row):
    """Formats a sqlite3.Row object into a readable string."""
    if not row:
        return "No result"
    return ", ".join(f"{key}: {row[key]}" for key in row.keys())

def log_db_operation(func):
    """A decorator to log database operations if DATABASE_LOGGING is True."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not config.DATABASE_LOGGING:
            return func(*args, **kwargs)

        arg_repr = [repr(a) for a in args]
        kwarg_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(arg_repr + kwarg_repr)
        print(f"--- DB LOG: Calling {func.__name__}({signature})")

        try:
            result = func(*args, **kwargs)
            if isinstance(result, list) and all(isinstance(r, sqlite3.Row) for r in result):
                print(f"--- DB LOG: {func.__name__} returned {len(result)} row(s):")
                for row in result:
                    print(f"  - {_format_row(row)}")
            elif isinstance(result, sqlite3.Row):
                 print(f"--- DB LOG: {func.__name__} returned: {_format_row(result)}")
            else:
                print(f"--- DB LOG: {func.__name__} returned: {result!r}")
            return result
        except Exception as e:
            print(f"--- DB LOG: {func.__name__} raised an exception: {e!r}")
            raise
    return wrapper

def _execute_query(cursor, query, params=None, fetch=None):
    """
    Executes a query and logs it.

    Args:
        cursor: The database cursor.
        query (str): The SQL query to execute.
        params (tuple, optional): The parameters for the query. Defaults to None.
        fetch (str, optional): Type of fetch ('one', 'all'). Defaults to None.
    """
    if config.DATABASE_LOGGING:
        print(f"--- DB EXEC: Query: {query.strip()}")
        if params:
            print(f"--- DB EXEC: Params: {params}")

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    if fetch == 'one':
        return cursor.fetchone()
    if fetch == 'all':
        return cursor.fetchall()

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
    Initializes the database. If the database or 'files' table does not exist,
    it creates a new, clean structure. If the table exists and contains data,
    it does nothing to prevent overwriting.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        table_exists = _execute_query(cursor, "SELECT name FROM sqlite_master WHERE type='table' AND name='files'", fetch='one')

        if table_exists:
            has_data = _execute_query(cursor, "SELECT 1 FROM files LIMIT 1", fetch='one')
            if has_data:
                print("Database already exists and contains data. Initialization skipped.")
                return

        _execute_query(cursor, """
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
    print(f"Database has been initialized at: {config.DATABASE_FILE}")

@log_db_operation
def add_file(file_path):
    """
    Adds a new file to the database if it doesn't already exist.
    Automatically calculates duration and sets the 'is_selected' flag.
    """
    duration = get_file_duration(file_path)
    is_selected = not (duration > config.MAX_FILE_DURATION_SECONDS)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            _execute_query(
                cursor,
                "INSERT INTO files (source_file_path, duration_seconds, is_selected) VALUES (?, ?, ?)",
                (file_path, duration, is_selected)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # File already exists

@log_db_operation
def update_file_duration(file_path, duration):
    """Updates the duration for a given file."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "UPDATE files SET duration_seconds = ? WHERE source_file_path = ?",
            (duration, file_path)
        )
        conn.commit()

@log_db_operation
def update_file_durations_bulk(files_data):
    """Bulk updates durations for a list of files."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        update_data = [(duration, path) for path, duration in files_data]
        cursor.executemany(
            "UPDATE files SET duration_seconds = ? WHERE source_file_path = ?",
            update_data
        )
        conn.commit()

@log_db_operation
def update_file_transcription(file_path, transcription_text):
    """Saves the transcription for a file and marks it as processed."""
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
    """Sets the selection flag for a single file."""
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
    """Gets a list of files that are selected and not loaded."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_selected = 1 AND is_loaded = 0 ORDER BY source_file_path", fetch='all')
        return [row['source_file_path'] for row in rows]

@log_db_operation
def get_files_to_process():
    """Gets a list of files that are loaded and not processed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = _execute_query(cursor, "SELECT source_file_path FROM files WHERE is_loaded = 1 AND is_processed = 0 ORDER BY source_file_path", fetch='all')
        return [row['source_file_path'] for row in rows]

@log_db_operation
def set_files_as_loaded(file_paths, tmp_file_paths):
    """Marks a list of files as loaded and saves their temporary paths."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        update_data = list(zip([True]*len(file_paths), tmp_file_paths, file_paths))
        cursor.executemany(
            "UPDATE files SET is_loaded = ?, tmp_file_path = ? WHERE source_file_path = ?",
            update_data
        )
        conn.commit()

@log_db_operation
def get_all_files():
    """Gets all files from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return _execute_query(cursor, "SELECT * FROM files ORDER BY source_file_path", fetch='all')

@log_db_operation
def clear_database_and_tmp_folder():
    """
    Deletes the entire temporary folder (including the database and .wav files)
    and then recreates an empty database.
    """
    if os.path.exists(config.TMP_DIR):
        shutil.rmtree(config.TMP_DIR)
        print(f"Temporary folder deleted: {config.TMP_DIR}")
    os.makedirs(config.TMP_DIR, exist_ok=True)
    initialize_database()

@log_db_operation
def unselect_all_files():
    """Unselects all files in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(cursor, "UPDATE files SET is_selected = 0")
        conn.commit()

@log_db_operation
def delete_file(file_path):
    """
    Deletes a file from the database and physically from the disk.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        result = _execute_query(cursor, "SELECT tmp_file_path FROM files WHERE source_file_path = ?", (file_path,), fetch='one')
        tmp_file_path = result['tmp_file_path'] if result else None

        _execute_query(cursor, "DELETE FROM files WHERE source_file_path = ?", (file_path,))
        conn.commit()

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted source file: {file_path}")
    except OSError as e:
        print(f"Error deleting source file {file_path}: {e}")

    if tmp_file_path:
        try:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                print(f"Deleted temporary file: {tmp_file_path}")
        except OSError as e:
            print(f"Error deleting temporary file {tmp_file_path}: {e}")