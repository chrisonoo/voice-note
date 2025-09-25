# Ten plik jest głównym punktem wejścia do aplikacji.
# Jego zadaniem jest zaimportowanie potrzebnych funkcji z poszczególnych modułów
# i wywołanie ich w odpowiedniej kolejności, aby przeprowadzić cały proces transkrypcji.

# Importujemy potrzebne funkcje z naszych modułów.
# Dzięki plikom __init__.py w każdym module, możemy to zrobić w bardzo czytelny sposób.
import argparse
import sys
import os
from src.audio import create_audio_file_list, encode_audio_files, validate_file_durations
from src.transcribe import TranscriptionProcessor
from src import config

def main_cli(args):
    """
    Główna funkcja orkiestrująca całym procesem transkrypcji w trybie CLI.
    """
    print("--- Rozpoczynam proces transkrypcji w trybie CLI ---")

    # W trybie CLI symulujemy starą logikę - szukamy plików w folderze `rec/input`
    cli_input_dir = os.path.join(os.path.dirname(__file__), 'rec', 'input')
    if not os.path.exists(cli_input_dir):
        os.makedirs(cli_input_dir)
        print(f"Utworzono folder wejściowy: {cli_input_dir}")
        print("Proszę umieścić pliki audio w tym folderze i uruchomić aplikację ponownie.")
        sys.exit(0)

    # === KROK 1: Wyszukiwanie plików audio ===
    print(f"Wyszukiwanie plików w folderze: {cli_input_dir}")
    audio_files = []
    for root, _, files in os.walk(cli_input_dir):
        for file in files:
            extension = os.path.splitext(file)[1].lower()
            if config.AUDIO_EXTENSIONS is None or extension in config.AUDIO_EXTENSIONS:
                full_path = os.path.abspath(os.path.join(root, file))
                audio_files.append(full_path)

    if not audio_files:
        print("Nie znaleziono plików audio do przetworzenia.")
        sys.exit(0)

    # Tworzymy listę plików w folderze tymczasowym
    create_audio_file_list(audio_files)

    # === KROK 1.5: Walidacja długości plików ===
    if not args.allow_long:
        print("\n--- Walidacja długości plików (limit: 5 minut) ---")
        long_files = validate_file_durations()
        if long_files:
            print("BŁĄD: Znaleziono pliki przekraczające 5 minut:")
            for f in long_files:
                print(f"  - {f}")
            print("\nProces przerwany. Użyj flagi -l lub --allow-long, aby zignorować to ograniczenie.")
            sys.exit(1) # Zakończ program
        else:
            print("Wszystkie pliki mieszczą się w limicie 5 minut.")


    # === KROK 2: Konwersja plików audio ===
    # Wywołujemy funkcję, która czyta listę plików z poprzedniego kroku
    # i konwertuje każdy z nich do standardowego formatu .wav za pomocą FFMPEG.
    # To zapewnia, że API Whisper otrzyma pliki w jednolitym, obsługiwanym formacie.
    encode_audio_files()

    # === KROK 3: Transkrypcja plików ===
    # Tworzymy instancję (obiekt) klasy TranscriptionProcessor.
    # Ta klasa zarządza całym procesem transkrypcji.
    processor = TranscriptionProcessor()

    # Wywołujemy metodę, która najpierw tworzy listę przekonwertowanych plików,
    # a następnie wysyła każdy z nich do API OpenAI Whisper i zapisuje wyniki.
    processor.process_transcriptions()

    # Na koniec informujemy użytkownika, że cały proces został zakończony pomyślnie.
    print("\n--- Proces transkrypcji zakończony pomyślnie! ---")


# Ten warunek sprawdza, czy plik `main.py` został uruchomiony bezpośrednio
# (np. komendą `python main.py`), a nie zaimportowany do innego pliku.
# To standardowa, dobra praktyka w Pythonie.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transkrypcja plików audio z użyciem API OpenAI Whisper.")
    parser.add_argument(
        "-l", "--allow-long",
        action="store_true",
        help="Zezwól na przetwarzanie plików dłuższych niż 5 minut (tylko tryb CLI)."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Uruchom aplikację w trybie graficznego interfejsu użytkownika (GUI)."
    )
    args = parser.parse_args()

    if args.gui:
        # Importujemy i uruchamiamy GUI
        from src.gui.main_window import main as main_gui
        main_gui()
    else:
        # Uruchamiamy tryb wiersza poleceń
        main_cli(args)