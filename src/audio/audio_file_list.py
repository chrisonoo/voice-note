import os
from src import config


def get_audio_file_list():
    """
    Przeszukuje katalog wejściowy zdefiniowany w konfiguracji, znajduje pliki
    audio o określonych rozszerzeniach i zapisuje ich pełne ścieżki do pliku.
    """
    print("Krok 1: Wyszukiwanie plików audio do przetworzenia...")
    with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w', encoding='utf-8') as f:
        for root, _, files in os.walk(config.INPUT_DIR):
            for file in files:
                extension = os.path.splitext(file)[1].lower()
                if config.AUDIO_EXTENSIONS is None or extension in config.AUDIO_EXTENSIONS:
                    full_path = os.path.abspath(os.path.join(root, file))
                    f.write(full_path + '\n')
    print(f"Znaleziono i zapisano listę plików w: {config.AUDIO_LIST_TO_ENCODE_FILE}")