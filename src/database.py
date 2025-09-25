import sqlite3
import os
import shutil
from datetime import datetime
from . import config

def get_db_connection():
    """Nawiązuje połączenie z bazą danych."""
    conn = sqlite3.connect(config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Inicjalizuje bazę danych. Tworzy folder tmp, usuwa istniejący plik bazy
    danych (jeśli istnieje) i tworzy nową, czystą strukturę tabel.
    """
    # Upewnij się, że folder tymczasowy istnieje
    os.makedirs(config.TMP_DIR, exist_ok=True)

    # Usuń stary plik bazy danych, jeśli istnieje, aby zapewnić czysty start
    if os.path.exists(config.DATABASE_FILE):
        os.remove(config.DATABASE_FILE)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Stwórz tabelę 'files'
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'selected',
        is_selected_in_gui BOOLEAN NOT NULL DEFAULT 0,
        transcription TEXT,
        duration_seconds REAL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    print(f"Baza danych została zainicjalizowana w: {config.DATABASE_FILE}")

def add_file(file_path):
    """Dodaje nowy plik do bazy danych ze statusem 'selected'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    try:
        cursor.execute("""
        INSERT INTO files (file_path, status, created_at, updated_at)
        VALUES (?, 'selected', ?, ?)
        """, (file_path, now, now))
        conn.commit()
    except sqlite3.IntegrityError:
        # Plik już istnieje w bazie, ignorujemy błąd
        pass
    finally:
        conn.close()

def update_file_duration(file_path, duration):
    """Aktualizuje czas trwania dla danego pliku."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
    UPDATE files
    SET duration_seconds = ?, updated_at = ?
    WHERE file_path = ?
    """, (duration, now, file_path))
    conn.commit()
    conn.close()

def update_file_status(file_path, status):
    """Aktualizuje status dla danego pliku."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
    UPDATE files
    SET status = ?, updated_at = ?
    WHERE file_path = ?
    """, (status, now, file_path))
    conn.commit()
    conn.close()

def update_transcription(file_path, transcription_text):
    """Zapisuje transkrypcję dla pliku i zmienia jego status na 'processed'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
    UPDATE files
    SET transcription = ?, status = 'processed', updated_at = ?
    WHERE file_path = ?
    """, (transcription_text, now, file_path))
    conn.commit()
    conn.close()

def set_gui_selection(file_path, is_selected):
    """Ustawia flagę zaznaczenia pliku w GUI."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("""
    UPDATE files
    SET is_selected_in_gui = ?, updated_at = ?
    WHERE file_path = ?
    """, (is_selected, now, file_path))
    conn.commit()
    conn.close()

def get_files_by_status(status):
    """Pobiera listę ścieżek plików o określonym statusie."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM files WHERE status = ?", (status,))
    files = [row['file_path'] for row in cursor.fetchall()]
    conn.close()
    return files

def get_all_files():
    """Pobiera wszystkie pliki z bazy danych."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM files ORDER BY file_path").fetchall()
    conn.close()
    return rows

def clear_database_and_tmp_folder():
    """
    Usuwa cały folder tymczasowy (w tym bazę danych i pliki .wav),
    a następnie odtwarza pustą bazę danych.
    """
    if os.path.exists(config.TMP_DIR):
        shutil.rmtree(config.TMP_DIR)
        print(f"Folder tymczasowy usunięty: {config.TMP_DIR}")
    initialize_database()

def set_gui_selection_for_list(file_paths, is_selected):
    """Ustawia flagę zaznaczenia dla listy plików."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    update_data = [(is_selected, now, file_path) for file_path in file_paths]
    cursor.executemany("""
    UPDATE files
    SET is_selected_in_gui = ?, updated_at = ?
    WHERE file_path = ?
    """, update_data)
    conn.commit()
    conn.close()

def clear_all_gui_selections():
    """Resetuje flagę zaznaczenia dla wszystkich plików."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("UPDATE files SET is_selected_in_gui = 0, updated_at = ?", (now,))
    conn.commit()
    conn.close()

def get_gui_selected_files(status):
    """Pobiera listę ścieżek plików o określonym statusie, które są zaznaczone w GUI."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM files WHERE status = ? AND is_selected_in_gui = 1", (status,))
    files = [row['file_path'] for row in cursor.fetchall()]
    conn.close()
    return files