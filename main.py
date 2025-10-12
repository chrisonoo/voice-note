# Ten plik jest głównym punktem wejścia do aplikacji (ang. "entry point").
# Uruchomienie `python main.py` rozpoczyna działanie programu.
# Jego zadaniem jest przetworzenie argumentów wiersza poleceń,
# a następnie uruchomienie aplikacji w odpowiednim trybie:
# graficznym (GUI) lub wiersza poleceń (CLI).

# Importujemy potrzebne moduły.
import argparse  # Standardowa biblioteka Pythona do parsowania argumentów wiersza poleceń.
import sys  # Moduł dający dostęp do funkcji systemowych, np. `sys.exit` do zamykania programu.
import os  # Moduł do interakcji z systemem operacyjnym, np. sprawdzania ścieżek.
from src.audio import encode_audio_files  # Funkcje do obsługi plików audio.
from src.transcribe import TranscriptionProcessor  # Główna klasa zarządzająca procesem transkrypcji.
from src import database  # Moduł do obsługi bazy danych.
from src.metadata import process_and_update_all_metadata  # Moduł do obsługi metadanych.
from src.utils.temp_file_manager import cleanup_temp_files_on_startup  # Czyszczenie plików tymczasowych

def main_cli(args):
    """
    Główna funkcja orkiestrująca całym procesem transkrypcji w trybie wiersza poleceń (CLI).
    Jest wywoływana, gdy aplikacja jest uruchamiana bez flagi --gui.

    Argumenty:
        args: Obiekt zawierający sparsowane argumenty z wiersza poleceń.
    """
    print("--- Rozpoczynam proces transkrypcji w trybie CLI ---")

    # Sprawdzamy, czy użytkownik podał wymaganą ścieżkę do folderu wejściowego.
    if not args.input_dir:
        print("BŁĄD: Brak ścieżki do folderu źródłowego.")
        print("Użyj: python main.py --input-dir /ścieżka/do/folderu/z/plikami")
        sys.exit(1)  # `sys.exit(1)` zamyka program z kodem błędu.
    
    # Konwertujemy podaną ścieżkę na ścieżkę absolutną, aby uniknąć problemów.
    input_dir = os.path.abspath(args.input_dir)
    
    # Sprawdzamy, czy podana ścieżka istnieje i czy jest folderem.
    if not os.path.exists(input_dir):
        print(f"BŁĄD: Podana ścieżka nie istnieje: {input_dir}")
        sys.exit(1)
    if not os.path.isdir(input_dir):
        print(f"BŁĄD: Podana ścieżka nie jest folderem: {input_dir}")
        sys.exit(1)
    
    print(f"Używam folderu źródłowego: {input_dir}")

    # Używamy dedykowanej funkcji do wyszukania plików audio w podanym folderze i dodania ich do bazy.
    # Importujemy ją tutaj, wewnątrz funkcji, ponieważ jest używana tylko w trybie CLI.
    from src.audio import get_audio_file_list_cli
    get_audio_file_list_cli(input_dir)

    # === KROK 1.5: Przetwarzanie metadanych i walidacja ===
    # Wywołujemy funkcję, która oblicza metadane (start, stop, przerwy, etc.)
    # i jednocześnie waliduje długość plików.
    long_files = process_and_update_all_metadata(allow_long=args.allow_long)

    # Jeśli znaleziono długie pliki i użytkownik nie zezwolił na ich przetwarzanie...
    if not args.allow_long and long_files:
        print("\nBŁĄD: Znaleziono pliki przekraczające 5 minut:")
        for f in long_files:
            print(f"  - {f}")
        print("\nProces przerwany. Użyj flagi -l lub --allow-long, aby zignorować to ograniczenie.")
        sys.exit(1)
    else:
        print("Wszystkie pliki gotowe do dalszego przetwarzania.")

    # === KROK 2: Konwersja plików audio ===
    # Wywołujemy funkcję, która pobiera pliki z bazy i konwertuje je do formatu audio gotowego do transkrypcji.
    encode_audio_files()

    # === KROK 3: Transkrypcja plików ===
    # Tworzymy instancję (obiekt) klasy `TranscriptionProcessor`.
    processor = TranscriptionProcessor()
    # Wywołujemy metodę, która pobiera przekonwertowane pliki i wysyła je do API Whisper.
    processor.process_transcriptions(allow_long=args.allow_long)

    print("\n--- Proces transkrypcji zakończony pomyślnie! ---")


# Warunek `if __name__ == "__main__":` jest standardową i bardzo ważną konstrukcją w Pythonie.
# Kod wewnątrz tego bloku wykona się tylko wtedy, gdy plik `main.py` jest uruchamiany
# bezpośrednio (np. komendą `python main.py`). Jeśli plik byłby importowany
# w innym module, ten kod zostałby zignorowany.
if __name__ == "__main__":
    # Inicjalizujemy bazę danych na samym początku, niezależnie od trybu (CLI/GUI).
    database.initialize_database()

    # Czyścimy stare pliki tymczasowe przy starcie aplikacji
    cleanup_temp_files_on_startup()

    # Tworzymy parser argumentów. To on "uczy" nasz program, jakich flag oczekiwać.
    parser = argparse.ArgumentParser(description="Transkrypcja plików audio z użyciem API OpenAI Whisper.")

    # Dodajemy argumenty (flagi), które program będzie rozpoznawał.
    parser.add_argument(
        "-l", "--allow-long",
        action="store_true",  # `action="store_true"` oznacza, że flaga nie przyjmuje wartości (jest przełącznikiem).
        help="Zezwól na przetwarzanie plików dłuższych niż 5 minut (tylko tryb CLI)."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Uruchom aplikację w trybie graficznego interfejsu użytkownika (GUI)."
    )
    parser.add_argument(
        "--input-dir",
        type=str,  # Oczekujemy wartości tekstowej (ścieżki).
        help="Ścieżka do folderu zawierającego pliki audio do transkrypcji (tylko tryb CLI)."
    )

    # `parser.parse_args()` analizuje argumenty podane w wierszu poleceń i zwraca obiekt z wynikami.
    args = parser.parse_args()

    # Sprawdzamy, czy użytkownik podał flagę `--gui`.
    if args.gui:
        # Jeśli tak, importujemy i uruchamiamy główną funkcję z modułu GUI.
        # Import jest tutaj, aby nie ładować ciężkich bibliotek GUI, gdy używamy tylko trybu CLI.
        from src.gui.core.main_window import main as main_gui
        main_gui()
    else:
        # Jeśli nie, uruchamiamy tryb wiersza poleceń, przekazując mu sparsowane argumenty.
        main_cli(args)