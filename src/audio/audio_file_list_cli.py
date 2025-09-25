# Ten moduł zawiera funkcje związane z wyszukiwaniem i listowaniem plików audio
# przeznaczone wyłącznie dla trybu wiersza poleceń (CLI).

import os
from src import config, database

def get_audio_file_list_cli(input_directory):
    """
    Przeszukuje podany katalog wejściowy, znajduje wszystkie pasujące pliki audio
    i dodaje ich ścieżki do bazy danych.
    """
    print("Krok 1 (CLI): Wyszukiwanie plików audio i dodawanie do bazy danych...")

    found_files_count = 0
    for root, _, files in os.walk(input_directory):
        for file in files:
            extension = os.path.splitext(file)[1].lower()
            if config.AUDIO_EXTENSIONS is None or extension in config.AUDIO_EXTENSIONS:
                full_path = os.path.abspath(os.path.join(root, file))
                database.add_file(full_path)
                found_files_count += 1

    print(f"Znaleziono i dodano do bazy danych {found_files_count} plików.")