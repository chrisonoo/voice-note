# Database queries module - data retrieval and bulk operations

from .connection import get_db_connection, _execute_query, log_db_operation

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
    """Oznacza listę plików jako wczytane (skonwertowane) i zapisuje ścieżki do ich przetworzonych wersji audio."""
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
