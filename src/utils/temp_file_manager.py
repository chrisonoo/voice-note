# Moduł do zarządzania plikami tymczasowymi

import os
import time
import glob
from src import config

def cleanup_all_temp_files():
    """
    Czyści wszystkie tymczasowe pliki audio bez względu na ich wiek.
    Używane podczas resetowania aplikacji.
    """
    if not os.path.exists(config.AUDIO_TMP_DIR):
        return

    cleaned_count = 0

    # Znajdź wszystkie przetworzone pliki audio w katalogu tymczasowym
    processed_audio_pattern = os.path.join(config.AUDIO_TMP_DIR, "*.m4a")
    for processed_audio_file in glob.glob(processed_audio_pattern):
        try:
            os.remove(processed_audio_file)
            cleaned_count += 1
            print(f"Usunięto plik tymczasowy: {os.path.basename(processed_audio_file)}")
        except OSError as e:
            print(f"Błąd podczas usuwania {processed_audio_file}: {e}")

    if cleaned_count > 0:
        print(f"Wyczyszczono {cleaned_count} plików tymczasowych.")
