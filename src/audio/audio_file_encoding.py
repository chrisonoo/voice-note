import os
import subprocess
from src import config


def encode_audio_files():
    """
    Czyta listę plików z pliku stanu, a następnie konwertuje każdy plik
    audio do formatu WAV za pomocą FFMPEG, zgodnie z ustawieniami w konfiguracji.
    Zachowuje strukturę katalogów.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu WAV...")
    with open(config.AUDIO_LIST_TO_ENCODE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            original_path = line.strip()
            relative_path = os.path.relpath(original_path, start=config.INPUT_DIR)
            new_path = os.path.join(config.OUTPUT_DIR, relative_path)
            new_path = os.path.splitext(new_path)[0] + '.wav'

            os.makedirs(os.path.dirname(new_path), exist_ok=True)

            print(f"  Konwertowanie: {original_path} -> {new_path}")

            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{new_path}"'

            try:
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"    BŁĄD: Nie udało się przekonwertować pliku {original_path}.")
                print(f"    Komunikat FFMPEG: {e.stderr}")
                continue

    print("Zakończono konwersję plików.")