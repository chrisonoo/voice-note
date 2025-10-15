# Ten moduł zawiera funkcje związane z wyszukiwaniem i listowaniem plików audio.
# Jego funkcjonalność jest przeznaczona wyłącznie dla trybu wiersza poleceń (CLI),
# gdzie użytkownik podaje folder do przeszukania jako argument startowy.

import os  # Moduł do interakcji z systemem operacyjnym, niezbędny do przeszukiwania folderów.
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.

def get_audio_file_list_cli(input_directory):
    """
    Rekursywnie przeszukuje podany katalog wejściowy (`input_directory`),
    znajduje wszystkie pliki pasujące do zdefiniowanych rozszerzeń audio
    i dodaje ich pełne, absolutne ścieżki do bazy danych.
    """
    print("Krok 1 (CLI): Wyszukiwanie plików audio i dodawanie do bazy danych...")

    # Inicjalizujemy licznik znalezionych plików.
    found_files_count = 0
    # `os.walk(input_directory)` to potężna funkcja, która "spaceruje" po drzewie katalogów.
    # Dla każdego folderu (włącznie z podfolderami) zwraca trzy wartości:
    # - `root`: aktualnie przeszukiwany folder.
    # - `_`: lista podfolderów w `root` (używamy `_`, bo nie potrzebujemy tej informacji).
    # - `files`: lista plików w `root`.
    for root, _, files in os.walk(input_directory):
        # Iterujemy przez każdy plik znaleziony w danym folderze.
        for file in files:
            # `os.path.splitext(file)` dzieli nazwę pliku na część główną i rozszerzenie.
            # Bierzemy drugi element (`[1]`), czyli rozszerzenie (np. ".mp3").
            # `.lower()` zamienia je na małe litery, aby porównanie było niezależne od wielkości liter.
            extension = os.path.splitext(file)[1].lower()

            # Sprawdzamy, czy znalezione rozszerzenie znajduje się na naszej liście dozwolonych rozszerzeń w `config`.
            # Warunek `config.ALL_SUPPORTED_EXTENSIONS is None` jest zabezpieczeniem, gdyby lista była pusta (choć w tym projekcie nie jest).
            if config.ALL_SUPPORTED_EXTENSIONS is None or extension in config.ALL_SUPPORTED_EXTENSIONS:
                # Jeśli plik ma pasujące rozszerzenie:
                # 1. `os.path.join(root, file)` tworzy pełną ścieżkę do pliku.
                # 2. `os.path.abspath` konwertuje ją na ścieżkę absolutną (np. "C:\Users\...\plik.mp3").
                #    Jest to ważne, aby uniknąć problemów ze ścieżkami względnymi.
                full_path = os.path.abspath(os.path.join(root, file))
                # Dodajemy znalezioną ścieżkę do bazy danych. Funkcja `add_file` zajmie się resztą
                # (sprawdzeniem, czy plik już istnieje, obliczeniem czasu trwania itp.).
                database.add_file(full_path)
                # Zwiększamy licznik znalezionych plików.
                found_files_count += 1

    # Po zakończeniu przeszukiwania, informujemy użytkownika o wyniku.
    print(f"Znaleziono i dodano do bazy danych {found_files_count} plików.")