# Database module - contains database operations and management

# Import all functions to maintain backward compatibility
from .connection import get_db_connection
from .schema import initialize_database, ensure_files_table_exists, reset_files_table, clear_database_and_tmp_folder
from .operations import add_file, update_file_transcription, set_file_selected, delete_file, cache_file_duration, optimize_database, validate_file_access
from .queries import get_files_to_load, get_files_to_process, set_files_as_loaded, get_all_files, get_files_needing_metadata, update_all_metadata_bulk, get_file_metadata, get_cached_duration

# Re-export for backward compatibility
__all__ = [
    'get_db_connection',
    'initialize_database',
    'ensure_files_table_exists',
    'reset_files_table',
    'clear_database_and_tmp_folder',
    'add_file',
    'update_file_transcription',
    'set_file_selected',
    'delete_file',
    'cache_file_duration',
    'optimize_database',
    'validate_file_access',
    'get_files_to_load',
    'get_files_to_process',
    'set_files_as_loaded',
    'get_all_files',
    'get_files_needing_metadata',
    'update_all_metadata_bulk',
    'get_file_metadata',
    'get_cached_duration'
]
