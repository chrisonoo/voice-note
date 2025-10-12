# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os  # Moduł do interakcji z systemem operacyjnym, np. do operacji na ścieżkach plików.
import subprocess  # Moduł pozwalający na uruchamianie zewnętrznych programów, w tym przypadku FFMPEG.
import concurrent.futures  # Dodane dla równoległego przetwarzania
from concurrent.futures import ThreadPoolExecutor
from src import config, database  # Importujemy własne moduły: konfigurację i operacje na bazie danych.
from src.utils.error_handlers import with_error_handling, measure_performance  # Dekoratory

def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik i zwraca tuple (source, tmp) lub None przy błędzie.
    Funkcja przeznaczona do równoległego przetwarzania.
    """
    try:
        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}")

        # Budujemy komendę FFMPEG
        command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'

        # Uruchamiamy komendę FFMPEG z timeout'em
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=300)

        return (original_path, tmp_file_path)

    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT: Konwersja pliku {os.path.basename(original_path)} przekroczyła limit czasu (5 min)")
        return None
    except subprocess.CalledProcessError as e:
        print(f"    BŁĄD FFMPEG: Nie udało się przekonwertować pliku {os.path.basename(original_path)}.")
        print(f"    Komunikat: {e.stderr[:200]}...")  # Ogranicz długość komunikatu błędu
        return None
    except Exception as ex:
        print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {os.path.basename(original_path)}: {ex}")
        return None

@with_error_handling("Konwersja plików audio")
@measure_performance
def encode_audio_files():
    """
    Pobiera z bazy danych listę plików do przetworzenia, konwertuje je do formatu audio gotowego do transkrypcji
    za pomocą zewnętrznego narzędzia FFMPEG z równoległym przetwarzaniem,
    a następnie aktualizuje ich status w bazie danych.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu gotowego do transkrypcji...")

    # Pobieramy z bazy danych listę plików, które zostały zaznaczone przez użytkownika i nie były jeszcze konwertowane.
    files_to_encode = database.get_files_to_load()
    if not files_to_encode:
        print("Brak nowych plików do konwersji.")
        return

    # Upewniamy się, że folder na przekonwertowane pliki audio istnieje.
    os.makedirs(config.AUDIO_TMP_DIR, exist_ok=True)

    print(f"Rozpoczynam równoległą konwersję {len(files_to_encode)} plików...")

    # Przetwarzaj pliki równolegle - maksymalnie 4 wątki lub tyle ile plików
    max_workers = min(4, len(files_to_encode))
    successful_conversions = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Tworzymy futures dla wszystkich plików
        futures = []
        for original_path in files_to_encode:
            future = executor.submit(_convert_single_file, original_path)
            futures.append((future, original_path))

        # Oczekujemy na wyniki
        for future, original_path in futures:
            try:
                result = future.result(timeout=300)  # 5 min timeout na całą operację
                if result:
                    successful_conversions.append(result)
            except concurrent.futures.TimeoutError:
                print(f"    TIMEOUT: Przetwarzanie pliku {os.path.basename(original_path)} przekroczyło limit czasu")
            except Exception as e:
                print(f"    BŁĄD WĄTKU: {e}")

    # Masowa aktualizacja bazy danych
    if successful_conversions:
        source_paths, tmp_paths = zip(*successful_conversions)
        database.set_files_as_loaded(source_paths, tmp_paths)
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    if len(successful_conversions) < len(files_to_encode):
        failed_count = len(files_to_encode) - len(successful_conversions)
        print(f"Nie udało się przekonwertować: {failed_count} plików.")

    print("Zakończono konwersję plików.")