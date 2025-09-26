# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.

import os
import subprocess
from src import config, database

def encode_audio_files():
    """
    Pobiera pliki z bazy danych, konwertuje je do formatu WAV
    za pomocą FFMPEG i oznacza je jako 'załadowane' po pomyślnej konwersji,
    zapisując ścieżkę do pliku tymczasowego.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu WAV...")

    files_to_encode = database.get_files_to_load()
    if not files_to_encode:
        print("Brak nowych plików do konwersji.")
        return

    os.makedirs(config.AUDIO_TMP_DIR, exist_ok=True)

    successful_conversions = []

    for original_path in files_to_encode:
        try:
            base_name = os.path.basename(original_path)
            standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
            output_filename = f"{standardized_name}.wav"
            tmp_file_path = os.path.join(config.AUDIO_TMP_DIR, output_filename)

            print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(tmp_file_path)}")

            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{tmp_file_path}"'
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

            successful_conversions.append((original_path, tmp_file_path))

        except subprocess.CalledProcessError as e:
            print(f"    BŁĄD: Nie udało się przekonwertować pliku {original_path}.")
            print(f"    Komunikat FFMPEG: {e.stderr}")
            continue
        except Exception as ex:
            print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {original_path}: {ex}")
            continue

    if successful_conversions:
        source_paths, tmp_paths = zip(*successful_conversions)
        database.set_files_as_loaded(source_paths, tmp_paths)
        print(f"Pomyślnie przekonwertowano i oznaczono jako załadowane: {len(successful_conversions)} plików.")

    print("Zakończono konwersję plików.")