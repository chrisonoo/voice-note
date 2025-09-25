# Ten plik jest głównym punktem wejścia do aplikacji.
# Jego zadaniem jest zaimportowanie potrzebnych funkcji z poszczególnych modułów
# i wywołanie ich w odpowiedniej kolejności, aby przeprowadzić cały proces transkrypcji.

# Importujemy potrzebne funkcje z naszych modułów.
# Dzięki plikom __init__.py w każdym module, możemy to zrobić w bardzo czytelny sposób.
import argparse
import sys
from src.audio import get_audio_file_list, encode_audio_files, validate_file_durations
from src.transcribe import TranscriptionProcessor


def main():
    """
    Główna funkcja orkiestrująca całym procesem transkrypcji.
    Wykonuje po kolei wszystkie kroki potrzebne do przetworzenia plików audio.
    """
    # === KROK 0: Parsowanie argumentów linii poleceń ===
    parser = argparse.ArgumentParser(description="Transkrypcja plików audio z użyciem API OpenAI Whisper.")
    parser.add_argument(
        "-l", "--allow-long",
        action="store_true",
        help="Zezwól na przetwarzanie plików dłuższych niż 5 minut."
    )
    args = parser.parse_args()

    # Wyświetlamy komunikat na starcie, aby użytkownik wiedział, że proces się rozpoczął.
    print("--- Rozpoczynam proces transkrypcji ---")

    # === KROK 1: Wyszukiwanie plików audio ===
    # Wywołujemy funkcję, która przeszukuje folder `rec/input` i tworzy listę
    # plików do przetworzenia. Lista ta jest zapisywana w pliku tekstowym.
    get_audio_file_list()

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
# To standardowa, dobra praktyka w Pythonie, która zapobiega automatycznemu
# uruchomieniu kodu, gdybyśmy chcieli w przyszłości zaimportować z tego pliku
# jakąś funkcję do innego modułu.
if __name__ == "__main__":
    # Jeśli warunek jest spełniony, wywołujemy naszą główną funkcję.
    main()