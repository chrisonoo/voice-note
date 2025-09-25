# Ten moduł zawiera funkcje związane z wyszukiwaniem i listowaniem plików audio
# przeznaczone wyłącznie dla trybu wiersza poleceń (CLI).

import os
from src import config

def get_audio_file_list_cli(input_directory):
    """
    Przeszukuje podany katalog wejściowy, znajduje wszystkie pasujące pliki audio
    i zapisuje ich pełne ścieżki do pliku stanu zdefiniowanego w `config`.
    """
    print("Krok 1 (CLI): Wyszukiwanie plików audio do przetworzenia...")

    with open(config.SELECTED_LIST, 'w', encoding='utf-8') as f:
        for root, _, files in os.walk(input_directory):
            for file in files:
                extension = os.path.splitext(file)[1].lower()
                if config.AUDIO_EXTENSIONS is None or extension in config.AUDIO_EXTENSIONS:
                    full_path = os.path.abspath(os.path.join(root, file))
                    f.write(full_path + '\n')

    print(f"Znaleziono i zapisano listę plików w: {config.SELECTED_LIST}")