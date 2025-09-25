# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.

import os
import subprocess
from src import config, database

def encode_audio_files(gui_mode=False):
    """
    Pobiera pliki z bazy danych, konwertuje je do formatu WAV
    za pomocą FFMPEG i aktualizuje ich status na 'encoded' po pomyślnej konwersji.

    Args:
        gui_mode (bool): Jeśli True, przetwarza tylko pliki zaznaczone w GUI.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu WAV...")

    if gui_mode:
        files_to_encode = database.get_gui_selected_files('selected')
        if not files_to_encode:
            print("Brak plików zaznaczonych w GUI do konwersji.")
            return
    else:
        files_to_encode = database.get_files_by_status('selected')
        if not files_to_encode:
            print("Brak nowych plików do konwersji.")
            return

    # Upewnij się, że katalog wyjściowy istnieje
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    for original_path in files_to_encode:
        try:
            base_name = os.path.basename(original_path)
            standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
            output_filename = f"{standardized_name}.wav"
            new_path = os.path.join(config.OUTPUT_DIR, output_filename)

            print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(new_path)}")

            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{new_path}"'

            subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

            # Po pomyślnej konwersji zaktualizuj status w bazie danych
            database.update_file_status(original_path, 'encoded')

        except subprocess.CalledProcessError as e:
            print(f"    BŁĄD: Nie udało się przekonwertować pliku {original_path}.")
            print(f"    Komunikat FFMPEG: {e.stderr}")
            # Opcjonalnie: można zaktualizować status na 'error'
            # database.update_file_status(original_path, 'encoding_error')
            continue
        except Exception as ex:
            print(f"    KRYTYCZNY BŁĄD podczas przetwarzania pliku {original_path}: {ex}")
            continue

    print("Zakończono konwersję plików.")