# Ten moduł zawiera funkcje związane z listowaniem plików audio.

from src import config  # Importujemy nasz centralny plik konfiguracyjny

def create_audio_file_list(file_paths):
    """
    Tworzy plik tekstowy zawierający listę absolutnych ścieżek do plików audio,
    które zostały wybrane przez użytkownika w interfejsie graficznym.

    Args:
        file_paths (list): Lista ciągów znaków, gdzie każdy ciąg to ścieżka do pliku.
    """
    print("Krok 1: Tworzenie listy plików audio do przetworzenia...")

    # Używamy instrukcji `with open(...)`, co jest dobrą praktyką, ponieważ
    # automatycznie zamyka plik po zakończeniu bloku, nawet jeśli wystąpi błąd.
    # 'w' oznacza tryb zapisu (write), a `encoding='utf-8'` zapewnia
    # poprawne obsłużenie polskich znaków w nazwach plików.
    with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'w', encoding='utf-8') as f:
        for path in file_paths:
            f.write(path + '\n')

    print(f"Zapisano listę {len(file_paths)} plików w: {config.AUDIO_LIST_TO_ENCODE_FILE}")