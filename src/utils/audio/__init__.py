# Ten plik __init__.py sprawia, że Python traktuje folder `audio` jako moduł (pakiet).
# Dzięki temu możemy w łatwy sposób importować zawarte w nim funkcje z innych części aplikacji.

# Importujemy konkretne funkcje z plików w tym folderze, aby były dostępne
# bezpośrednio po zaimportowaniu modułu `audio`, np. `from src.utils.audio import encode_audio_files`.
# To upraszcza importy w innych częściach kodu.

from .audio_file_encoding import encode_audio_files
from .duration_checker import get_file_duration
from .audio_file_list_cli import get_audio_file_list_cli