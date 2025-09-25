# Ten moduł odpowiada za konwersję (enkodowanie) plików audio do jednolitego formatu.

import os
import subprocess  # Moduł do uruchamiania zewnętrznych programów, w naszym przypadku FFMPEG
from src import config  # Importujemy nasz centralny plik konfiguracyjny


def encode_audio_files():
    """
    Czyta listę plików audio z pliku stanu (`config.SELECTED_LIST`),
    a następnie konwertuje każdy z nich do formatu WAV za pomocą FFMPEG,
    używając parametrów zdefiniowanych w `config.FFMPEG_PARAMS`.
    Nowe pliki są zapisywane w katalogu wyjściowym (`config.OUTPUT_DIR`),
    z zachowaniem oryginalnej struktury podkatalogów.
    """
    print("\nKrok 2: Konwertowanie plików audio do formatu WAV...")

    # Otwieramy plik z listą ścieżek do przetworzenia.
    # 'r' oznacza tryb odczytu (read).
    with open(config.SELECTED_LIST, 'r', encoding='utf-8') as f:
        # Przechodzimy przez każdą linię w pliku.
        for line in f:
            # `line.strip()` usuwa białe znaki (w tym znak nowej linii `\n`) z początku i końca linii.
            original_path = line.strip()

            # Budujemy ścieżkę wyjściową.
            base_name = os.path.basename(original_path)
            # Standaryzujemy nazwę: małe litery, spacje na podkreślenia, usuwamy oryginalne rozszerzenie.
            standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
            output_filename = f"{standardized_name}.wav"
            new_path = os.path.join(config.OUTPUT_DIR, output_filename)

            print(f"  Konwertowanie: {os.path.basename(original_path)} -> {os.path.basename(new_path)}")

            # Składamy pełną komendę FFMPEG do wykonania w systemie.
            # Używamy f-stringów do wstawienia naszych zmiennych.
            # Ważne: ścieżki do plików są w cudzysłowach, co chroni przed błędami,
            # jeśli nazwy plików zawierają spacje.
            command = f'ffmpeg -y -i "{original_path}" {config.FFMPEG_PARAMS} "{new_path}"'

            try:
                # `subprocess.run` uruchamia komendę w systemie.
                # `shell=True` jest potrzebne do interpretacji komendy jako całości.
                # `check=True` sprawia, że jeśli komenda zakończy się błędem, rzucony zostanie wyjątek.
                # `capture_output=True` i `text=True` przechwytują standardowe wyjście i wyjście błędów jako tekst.
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                # Jeśli FFMPEG zwróci błąd, przechwytujemy wyjątek.
                print(f"    BŁĄD: Nie udało się przekonwertować pliku {original_path}.")
                # Wyświetlamy komunikat błędu zwrócony przez FFMPEG, co bardzo pomaga w diagnozie.
                print(f"    Komunikat FFMPEG: {e.stderr}")
                # `continue` przerywa bieżącą iterację pętli i przechodzi do następnego pliku.
                continue

    print("Zakończono konwersję plików.")