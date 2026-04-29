# Ten plik jest głównym punktem wejścia do aplikacji dla developerów.
# Uruchomienie `python main.py` uruchamia aplikację w domyślnym trybie GUI.
# Dla pełnej funkcjonalności wiersza poleceń użyj komendy `vnote` z odpowiednimi flagami.
#
# Przykład użycia:
# - python main.py              # Uruchamia GUI
# - vnote --gui                 # Uruchamia GUI przez komendę vnote
# - vnote --input-dir /path     # Uruchamia CLI przez komendę vnote

from src import database  # Moduł do obsługi bazy danych.


def main():
    """
    Główna funkcja aplikacji Voice Note dla developerów.
    Domyślnie uruchamia tryb GUI.
    """
    # Inicjalizujemy bazę danych
    database.initialize_database()

    # Uruchamiamy GUI (domyślny tryb dla developerów)
    from src.gui.core import main_gui
    main_gui.main()


# Warunek `if __name__ == "__main__":` jest standardową i bardzo ważną konstrukcją w Pythonie.
# Kod wewnątrz tego bloku wykona się tylko wtedy, gdy plik `main.py` jest uruchamiany
# bezpośrednio (np. komendą `python main.py`). Jeśli plik byłby importowany
# w innym module, ten kod zostałby zignorowany.
if __name__ == "__main__":
    main()
