# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.
# Głównym celem jest upewnienie się, że wszystkie pliki, niezależnie od ich oryginalnego
# formatu (.mp3, .m4a itp.), zostaną przekonwertowane do standardowego formatu audio,
# który jest zoptymalizowany dla API Whisper.

import os
from pydub import AudioSegment
from pydub.effects import normalize
from src import config, database
from src.utils.error_handlers import with_error_handling, measure_performance
from src.utils.file_type_helper import is_video_file

def _convert_single_file(original_path):
    """
    Konwertuje pojedynczy plik audio lub wideo (wyciągając audio) do znormalizowanego formatu M4A
    używając Pydub (z PyAV jako backendem). Zwraca tuple (source, tmp) lub None w przypadku błędu.
    """
    try:
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
        output_filename = f"{standardized_name}.m4a"
        tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

        print(f"  Konwertowanie: {base_name} -> {output_filename}")

        if is_video_file(original_path):
            print(f"    Wykryto plik wideo - ekstrakcja i konwersja ścieżki audio.")

        # Krok 1: Wczytanie pliku (Pydub automatycznie użyje PyAV w tle)
        # Niezależnie od formatu, Pydub wczyta go do swojego wewnętrznego formatu.
        audio = AudioSegment.from_file(original_path)

        # Krok 2: Normalizacja głośności (do -12 dBFS, jak w poprzedniej implementacji)
        # `normalize` skaluje głośność tak, aby szczyt osiągnął 0 dBFS.
        # Aby osiągnąć cel -12 dBFS, możemy najpierw znormalizować, a potem obniżyć głośność.
        # Jednakże, dla uproszczenia i zachowania dynamiki, użyjemy standardowej normalizacji Pydub,
        # która jest efektywna w zapobieganiu przesterowaniom.
        if config.PYAV_ENABLE_LOUDNESS_NORMALIZATION:
            print("    Normalizowanie głośności...")
            audio = normalize(audio)

        # Krok 3: Eksport pliku do formatu M4A (Pydub znów użyje PyAV)
        print(f"    Eksportowanie do formatu M4A...")
        audio.export(
            tmp_file_path,
            format="m4a",
            codec=config.PYAV_AUDIO_CODEC,
            bitrate=str(config.PYAV_BIT_RATE)  # Bitrate musi być stringiem
        )

        return (original_path, tmp_file_path)

    except Exception as ex:
        print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {os.path.basename(original_path)}: {ex}")
        return None

@with_error_handling("Konwersja plików audio")
@measure_performance
def encode_audio_files(app=None):
    """
    Pobiera z bazy danych listę plików do przetworzenia, konwertuje je do formatu audio gotowego do transkrypcji
    za pomocą PyAV z sekwencyjnym przetwarzaniem,
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
                app.after(0, lambda: app.panel_manager.refresh_transcription_progress_views())
                app.after(0, lambda: app.update_all_counters())
        else:
            print(f"    ✗ Nie udało się przetworzyć: {os.path.basename(original_path)}")

    if successful_conversions:
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    if len(successful_conversions) < len(files_to_encode):
        failed_count = len(files_to_encode) - len(successful_conversions)
        print(f"Nie udało się przekonwertować: {failed_count} plików.")

    print("Zakończono konwersję plików.")