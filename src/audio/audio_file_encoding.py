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
from src.utils.file_type_helper import is_video_file  # Funkcja do wykrywania plików wideo

def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik i zwraca tuple (source, tmp) lub None przy błędzie.
    Funkcja przeznaczona do równoległego przetwarzania.
    Dla plików wideo ekstrahuje tylko ścieżkę audio (-vn), dla audio używa standardowych parametrów.
    """
    try:
        # Tworzymy standardową, bezpieczną nazwę pliku wyjściowego.
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}")

        # Sprawdzamy czy plik jest wideo
        is_video = is_video_file(original_path)

        # Budujemy komendę FFMPEG
        if is_video:
            # Dla plików wideo ekstrahujemy tylko audio (-vn ignoruje strumień wideo)
            command = f'ffmpeg -y -i "{original_path}" -vn {config.FFMPEG_PARAMS} "{tmp_file_path}"'
        else:
            # Dla plików audio używamy standardowych parametrów
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'

        # Obliczamy timeout proporcjonalny do długości pliku + 5 minut bufora
        # Dla pliku 139 min: ~147 min timeout, dla krótkich plików: minimum 10 min
        from src.audio.duration_checker import get_file_duration
        duration_sec = get_file_duration(original_path)
        timeout_sec = max(600, int(duration_sec * 1.1) + 300)  # 10% + 5 min bufora, minimum 10 min

        print(f"    Timeout dla tego pliku: {timeout_sec//60} minut")
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=timeout_sec)

        return (original_path, tmp_file_path)

    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT: Konwersja pliku {os.path.basename(original_path)} przekroczyła wyliczony limit czasu")
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
def encode_audio_files(app=None):
    """
    Pobiera z bazy danych listę plików do przetworzenia, konwertuje je do formatu audio gotowego do transkrypcji
    za pomocą zewnętrznego narzędzia FFMPEG z sekwencyjnym przetwarzaniem,
    aktualizując GUI po każdym przetworzonym pliku.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu gotowego do transkrypcji...")

    # Pobieramy z bazy danych listę plików, które zostały zaznaczone przez użytkownika i nie były jeszcze konwertowane.
    files_to_encode = database.get_files_to_load()
    if not files_to_encode:
        print("Brak nowych plików do konwersji.")
        return

    # Upewniamy się, że folder na przekonwertowane pliki audio istnieje.
    os.makedirs(config.AUDIO_TMP_DIR, exist_ok=True)

    print(f"Rozpoczynam sekwencyjną konwersję {len(files_to_encode)} plików...")

    successful_conversions = []

    # Przetwarzaj pliki sekwencyjnie
    for i, original_path in enumerate(files_to_encode, 1):
        print(f"Przetwarzanie pliku {i}/{len(files_to_encode)}: {os.path.basename(original_path)}")

        result = _convert_single_file(original_path)
        if result:
            source_path, tmp_path = result
            successful_conversions.append(result)

            # Aktualizuj bazę danych natychmiast po przetworzeniu pliku
            database.set_files_as_loaded([source_path], [tmp_path])
            print(f"    ✓ Przetworzono i dodano do bazy: {os.path.basename(source_path)}")

            # Odśwież GUI jeśli mamy referencję do aplikacji
            if app:
                app.after(0, lambda: app.invalidate_cache())
                app.after(0, lambda: app.refresh_all_views())
        else:
            print(f"    ✗ Nie udało się przetworzyć: {os.path.basename(original_path)}")

    if successful_conversions:
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    if len(successful_conversions) < len(files_to_encode):
        failed_count = len(files_to_encode) - len(successful_conversions)
        print(f"Nie udało się przekonwertować: {failed_count} plików.")

    print("Zakończono konwersję plików.")