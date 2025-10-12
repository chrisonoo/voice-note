# Moduł do zarządzania plikami tymczasowymi

import os
import time
import glob
from src import config

def cleanup_old_temp_files(max_age_hours=24):
    """
    Czyści stare tymczasowe pliki WAV.

    Argumenty:
        max_age_hours (int): Maksymalny wiek plików w godzinach.
    """
    if not os.path.exists(config.AUDIO_TMP_DIR):
        return

    cutoff_time = time.time() - (max_age_hours * 3600)
    cleaned_count = 0

    # Znajdź wszystkie przetworzone pliki audio w katalogu tymczasowym
    processed_audio_pattern = os.path.join(config.AUDIO_TMP_DIR, "*.m4a")
    for processed_audio_file in glob.glob(processed_audio_pattern):
        try:
            # Sprawdź czas modyfikacji
            if os.path.getmtime(processed_audio_file) < cutoff_time:
                os.remove(processed_audio_file)
                cleaned_count += 1
                print(f"Usunięto stary plik tymczasowy: {os.path.basename(processed_audio_file)}")
        except OSError as e:
            print(f"Błąd podczas usuwania {processed_audio_file}: {e}")

    if cleaned_count > 0:
        print(f"Wyczyszczono {cleaned_count} starych plików tymczasowych.")

def cleanup_temp_files_on_startup():
    """Czyści tymczasowe pliki przy starcie aplikacji."""
    try:
        cleanup_old_temp_files(max_age_hours=1)  # Pliki starsze niż 1 godzina
    except Exception as e:
        print(f"Błąd podczas czyszczenia plików tymczasowych przy starcie: {e}")

def get_temp_files_size():
    """
    Zwraca całkowity rozmiar plików tymczasowych w MB.

    Zwraca:
        float: Rozmiar w megabajtach.
    """
    if not os.path.exists(config.AUDIO_TMP_DIR):
        return 0.0

    total_size = 0
    for root, dirs, files in os.walk(config.AUDIO_TMP_DIR):
        for file in files:
            try:
                total_size += os.path.getsize(os.path.join(root, file))
            except OSError:
                pass

    return total_size / (1024 * 1024)  # Konwersja na MB

def cleanup_if_storage_low(min_free_mb=100):
    """
    Czyści tymczasowe pliki jeśli wolne miejsce na dysku jest niskie.

    Argumenty:
        min_free_mb (int): Minimalna ilość wolnego miejsca w MB.
    """
    try:
        # Sprawdź dostępne miejsce na dysku
        stat = os.statvfs(config.TMP_DIR)
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

        if free_mb < min_free_mb:
            print(f"Mało miejsca na dysku ({free_mb:.1f}MB). Czyści tymczasowe pliki...")
            cleanup_old_temp_files(max_age_hours=0.1)  # Pliki starsze niż 6 minut
    except AttributeError:
        # os.statvfs może nie być dostępne na Windows
        pass
    except Exception as e:
        print(f"Błąd podczas sprawdzania miejsca na dysku: {e}")
