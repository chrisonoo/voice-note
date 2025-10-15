# Metadata module - contains metadata processing and formatting logic

# Import all functions to maintain backward compatibility
from .processor import process_and_update_all_metadata

# Re-export for backward compatibility
__all__ = [
    'process_and_update_all_metadata'
]
