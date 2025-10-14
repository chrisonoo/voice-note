# Metadata module - contains metadata processing and formatting logic

# Import all functions to maintain backward compatibility
from .processor import process_and_update_all_metadata
from .formatter import format_transcription_header

# Re-export for backward compatibility
__all__ = [
    'process_and_update_all_metadata',
    'format_transcription_header'
]
