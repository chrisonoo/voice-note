# Ten plik jest głównym punktem wejścia do aplikacji (ang. "entry point").
# Uruchomienie `python main.py` rozpoczyna działanie programu.
# Jego zadaniem jest przetworzenie argumentów wiersza poleceń,
# a następnie uruchomienie aplikacji w odpowiednim trybie:
# graficznym (GUI) lub wiersza poleceń (CLI).

# Importujemy potrzebne moduły.
import argparse  # Standardowa biblioteka Pythona do parsowania argumentów wiersza poleceń.
from src import database  # Moduł do obsługi bazy danych.

# Warunek `if __name__ == "__main__":` jest standardową i bardzo ważną konstrukcją w Pythonie.
# Kod wewnątrz tego bloku wykona się tylko wtedy, gdy plik `main.py` jest uruchamiany
# bezpośrednio (np. komendą `python main.py`). Jeśli plik byłby importowany
# w innym module, ten kod zostałby zignorowany.
if __name__ == "__main__":
    # Inicjalizujemy bazę danych na samym początku, niezależnie od trybu (CLI/GUI).
    database.initialize_database()

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
        from src.gui.core.main_gui import main as main_gui
        main_gui()
    else:
        # Jeśli nie, uruchamiamy tryb wiersza poleceń, przekazując mu sparsowane argumenty.
        from src.cli.main_cli import main_cli
        main_cli(args)