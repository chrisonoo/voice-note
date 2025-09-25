# Ten moduł zawiera funkcje związane z wyszukiwaniem i listowaniem plików audio.

import os
from src import config  # Importujemy nasz centralny plik konfiguracyjny


def get_audio_file_list():
    """
    Przeszukuje katalog wejściowy zdefiniowany w konfiguracji (`config.INPUT_DIR`),
    znajduje wszystkie pliki pasujące do zdefiniowanych rozszerzeń
    (`config.AUDIO_EXTENSIONS`) i zapisuje ich pełne, absolutne ścieżki
    do pliku tekstowego (`config.AUDIO_LIST_TO_ENCODE_FILE`).
    """
    print("Krok 1: Wyszukiwanie plików audio do przetworzenia...")

    # Używamy instrukcji `with open(...)`, co jest dobrą praktyką, ponieważ
    # automatycznie zamyka plik po zakończeniu bloku, nawet jeśli wystąpi błąd.
    # 'w' oznacza tryb zapisu (write), a `encoding='utf-8'` zapewnia
    # poprawne obsłużenie polskich znaków w nazwach plików.
    with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w', encoding='utf-8') as f:
        # `os.walk(config.INPUT_DIR)` to funkcja, która rekursywnie przechodzi
        # przez podany katalog i wszystkie jego podkatalogi.
        # Zwraca trzy wartości dla każdego folderu: jego ścieżkę (`root`),
        # listę podfolderów (`_`, ignorujemy ją) i listę plików (`files`).
        for root, _, files in os.walk(config.INPUT_DIR):
            # Przechodzimy przez każdy plik znaleziony w danym folderze.
            for file in files:
                # `os.path.splitext(file)` rozdziela nazwę pliku na część główną
                # i rozszerzenie. Interesuje nas tylko rozszerzenie (indeks 1).
                # `.lower()` zamienia je na małe litery, aby uniknąć problemów
                # z wielkością liter (np. `.MP3` vs `.mp3`).
                extension = os.path.splitext(file)[1].lower()

                # Sprawdzamy, czy znalezione rozszerzenie znajduje się na naszej
                # liście dozwolonych rozszerzeń w pliku konfiguracyjnym.
                if config.AUDIO_EXTENSIONS is None or extension in config.AUDIO_EXTENSIONS:
                    # `os.path.join(root, file)` tworzy pełną ścieżkę do pliku.
                    # `os.path.abspath(...)` zamienia ją na ścieżkę absolutną
                    # (np. "C:\Users\...\projekt\rec\input\nagranie.mp3").
                    full_path = os.path.abspath(os.path.join(root, file))
                    # Zapisujemy tę ścieżkę do naszego pliku tekstowego,
                    # dodając na końcu znak nowej linii `\n`.
                    f.write(full_path + '\n')

    print(f"Znaleziono i zapisano listę plików w: {config.AUDIO_LIST_TO_ENCODE_FILE}")