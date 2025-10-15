# CLI main module - command line interface logic

import argparse  # Standardowa biblioteka Pythona do parsowania argumentów wiersza poleceń.
import sys  # Moduł dający dostęp do funkcji systemowych, np. `sys.exit` do zamykania programu.
import os  # Moduł do interakcji z systemem operacyjnym, np. sprawdzania ścieżek.
from src.utils.audio import encode_audio_files  # Funkcje do obsługi plików audio.
from src.services.transcription_service import TranscriptionService  # Główna klasa zarządzająca procesem transkrypcji.
from src import database  # Moduł do obsługi bazy danych.
from src.metadata import process_and_update_all_metadata  # Moduł do obsługi metadanych.

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
        sys.exit(1)

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
    from src.utils.audio import get_audio_file_list_cli
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
    # Tworzymy instancję klasy `TranscriptionService`.
    processor = TranscriptionService()
    # Wywołujemy metodę, która pobiera przekonwertowane pliki i wysyła je do API Whisper.
    processor.process_transcriptions(allow_long=args.allow_long)

    print("\n--- Proces transkrypcji zakończony pomyślnie! ---")
