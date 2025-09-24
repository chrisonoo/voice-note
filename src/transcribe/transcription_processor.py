# Ten moduł zawiera klasę `TranscriptionProcessor`, która jest "mózgiem" całej operacji.
# Odpowiada za zarządzanie całym procesem transkrypcji, od przygotowania list
# plików, przez wywoływanie transkrypcji dla każdego z nich, aż po zapisywanie
# wyników i aktualizowanie plików stanu.

import os
import shutil  # Moduł do operacji na plikach, takich jak kopiowanie
from src.whisper import Whisper
from src import config


class TranscriptionProcessor:
    """
    Klasa zarządzająca całym procesem transkrypcji plików audio.
    """
    def __init__(self):
        """
        Inicjalizuje procesor transkrypcji.
        Konfiguracja jest wczytywana bezpośrednio z pliku `src/config.py`,
        więc konstruktor nie musi przyjmować żadnych argumentów.
        """
        # Przechowujemy parametry dla API Whisper, aby mieć do nich łatwy dostęp.
        self.response_format = config.WHISPER_API_RESPONSE_FORMAT
        self.prompt = config.WHISPER_API_PROMPT
        self.temperature = config.WHISPER_API_TEMPERATURE

    def _prepare_transcription_list(self):
        """
        Metoda pomocnicza (oznaczona `_` na początku) do tworzenia listy plików
        do transkrypcji. Przeszukuje katalog `output` (gdzie znajdują się pliki
        po konwersji FFMPEG) i zapisuje listę plików .wav do pliku stanu.
        """
        print("\nKrok 3: Przygotowywanie listy plików do transkrypcji...")
        with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'w', encoding='utf-8') as f:
            for root, _, files in os.walk(config.OUTPUT_DIR):
                for file in files:
                    # Szukamy tylko plików .wav, bo tylko takie powinny być w folderze `output`.
                    if file.lower().endswith(".wav"):
                        full_path = os.path.abspath(os.path.join(root, file))
                        f.write(full_path + '\n')

        # Kopiujemy świeżo utworzoną listę plików do pliku, który będzie śledził
        # postęp przetwarzania. Na początku obie listy są identyczne.
        shutil.copyfile(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, config.PROCESSING_LIST_FILE)
        print(f"Lista plików do transkrypcji została zapisana w: {config.AUDIO_LIST_TO_TRANSCRIBE_FILE}")

    def process_transcriptions(self):
        """
        Główna metoda tej klasy. Przetwarza pliki z listy, wykonuje transkrypcję
        i zarządza plikami stanu, aby zapewnić odporność na błędy.
        """
        # Najpierw przygotowujemy listę plików do przetworzenia.
        self._prepare_transcription_list()

        print("\nKrok 4: Rozpoczynanie transkrypcji plików...")

        # Otwieramy plik z listą wszystkich plików .wav do przetworzenia.
        with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'r', encoding='utf8') as source_files:
            lines = source_files.readlines()

        # Usuwamy stary plik z wynikami, jeśli istnieje, aby każde uruchomienie
        # tworzyło świeży plik z transkrypcjami.
        if os.path.exists(config.TRANSCRIPTIONS_FILE):
            os.remove(config.TRANSCRIPTIONS_FILE)

        # Przechodzimy przez każdy plik z naszej listy.
        for line in lines:
            audio_file = line.strip()
            # Dla każdego pliku tworzymy nową instancję klasy Whisper.
            whisper = Whisper(audio_file)

            print(f"  Przetwarzanie pliku: {audio_file}")
            # Wywołujemy metodę `transcribe`, która wysyła plik do API OpenAI.
            transcription = whisper.transcribe()

            # Jeśli transkrypcja się powiodła (nie zwrócono `None`), przetwarzamy wynik.
            if transcription:
                # Otwieramy plik zbiorczy w trybie 'a' (append - dopisywanie na końcu).
                with open(config.TRANSCRIPTIONS_FILE, 'a', encoding='utf8') as f:
                    # Dodajemy nagłówek, aby łatwo było zidentyfikować, do którego pliku należy transkrypcja.
                    f.write(f"--- Transkrypcja dla: {os.path.basename(audio_file)} ---\n")
                    # Dopisujemy właściwy tekst transkrypcji.
                    f.write(f"{transcription.text}\n\n")

                print(f"    Sukces: Transkrypcja zapisana.")

                # Aktualizujemy pliki stanu, aby oznaczyć ten plik jako przetworzony.
                self._update_state_files(audio_file)
            else:
                # Jeśli wystąpił błąd, wyświetlamy komunikat i przechodzimy do następnego pliku.
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

        print("\nZakończono proces transkrypcji.")
        print(f"Wszystkie transkrypcje zostały zapisane w: {config.TRANSCRIPTIONS_FILE}")

    def _update_state_files(self, audio_file):
        """
        Metoda pomocnicza do aktualizowania plików stanu.
        Dodaje wpis do listy przetworzonych plików (`processed_list.txt`) i usuwa
        go z listy oczekujących na przetworzenie (`processing_list.txt`).
        Dzięki temu, w razie przerwania, wiemy, od którego miejsca wznowić pracę.
        """
        # Dopisujemy ścieżkę do pliku na końcu listy przetworzonych.
        with open(config.PROCESSED_LIST_FILE, 'a', encoding='utf8') as processed_files:
            processed_files.write(audio_file + '\n')

        # Odczytujemy wszystkie linie z listy "do przetworzenia".
        with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf8') as proc_file:
            processing_lines = proc_file.readlines()

        # Tworzymy nową listę, która zawiera tylko te linie, które NIE pasują
        # do właśnie przetworzonego pliku. To skutecznie usuwa przetworzony plik z listy.
        new_lines = [proc_line for proc_line in processing_lines if proc_line.strip() != audio_file]

        # Zapisujemy nową, skróconą listę z powrotem do pliku, nadpisując jego zawartość.
        with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf8') as file:
            file.writelines(new_lines)