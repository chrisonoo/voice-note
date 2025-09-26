# Ten plik jest głównym punktem wejścia do aplikacji.
# Jego zadaniem jest zaimportowanie potrzebnych funkcji z poszczególnych modułów
# i wywołanie ich w odpowiedniej kolejności, aby przeprowadzić cały proces transkrypcji.

# Importujemy potrzebne funkcje z naszych modułów.
# Dzięki plikom __init__.py w każdym module, możemy to zrobić w bardzo czytelny sposób.
import argparse
import sys
import os
from src.audio import encode_audio_files, validate_file_durations
from src.transcribe import TranscriptionProcessor
from src import config
from src import database

def main_cli(args):
    """
    Główna funkcja orkiestrująca całym procesem transkrypcji w trybie CLI.
    """
    print("--- Rozpoczynam proces transkrypcji w trybie CLI ---")

    # Walidacja argumentu --input-dir
    if not args.input_dir:
        print("BŁĄD: Brak ścieżki do folderu źródłowego.")
        print("Użyj: python main.py --input-dir /ścieżka/do/folderu/z/plikami")
        sys.exit(1)
    
    input_dir = os.path.abspath(args.input_dir)
    
    # Sprawdzenie czy podana ścieżka istnieje
    if not os.path.exists(input_dir):
        print(f"BŁĄD: Podana ścieżka nie istnieje: {input_dir}")
        sys.exit(1)
    
    if not os.path.isdir(input_dir):
        print(f"BŁĄD: Podana ścieżka nie jest folderem: {input_dir}")
        sys.exit(1)
    
    print(f"Używam folderu źródłowego: {input_dir}")

    # Użycie dedykowanej funkcji do wyszukania plików dla CLI
    from src.audio import get_audio_file_list_cli
    get_audio_file_list_cli(input_dir)

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
    # Inicjalizacja bazy danych na samym początku
    database.initialize_database()

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
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Ścieżka do folderu zawierającego pliki audio do transkrypcji (tylko tryb CLI)."
    )
    args = parser.parse_args()

    if args.gui:
        # Importujemy i uruchamiamy GUI
        from src.gui.core.main_window import main as main_gui
        main_gui()
    else:
        # Uruchamiamy tryb wiersza poleceń
        main_cli(args)