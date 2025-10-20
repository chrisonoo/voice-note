# Database module - contains database operations and management

# Import all functions to maintain backward compatibility
from .connection import get_db_connection
from .operations import (
    add_chunk_file,
    add_file,
    cache_file_duration,
    delete_file,
    mark_file_as_chunked,
    optimize_database,
    set_file_selected,
    update_file_transcription,
    validate_file_access,
)
from .queries import (
    get_all_files,
    get_cached_duration,
    get_file_metadata,
    get_files_needing_metadata,
    get_files_to_load,
    get_files_to_process,
    set_files_as_loaded,
    update_all_metadata_bulk,
)
from .schema import (
    clear_database_and_tmp_folder,
    ensure_files_table_exists,
    initialize_database,
    reset_files_table,
)

# Re-export for backward compatibility
__all__ = [
    "get_db_connection",
    "initialize_database",
    "ensure_files_table_exists",
    "reset_files_table",
    "clear_database_and_tmp_folder",
    "add_file",
    "add_chunk_file",
    "mark_file_as_chunked",
    "update_file_transcription",
    "set_file_selected",
    "delete_file",
    "cache_file_duration",
    "optimize_database",
    "validate_file_access",
    "get_files_to_load",
    "get_files_to_process",
    "set_files_as_loaded",
    "get_all_files",
    "get_files_needing_metadata",
    "update_all_metadata_bulk",
    "get_file_metadata",
    "get_cached_duration",
]
