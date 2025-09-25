# Ten moduł zawiera klasę `TranscriptionProcessor`, która jest "mózgiem" całej operacji.
# Odpowiada za zarządzanie procesem transkrypcji, od odczytania listy plików,
# przez wywołanie transkrypcji, aż po zapisywanie wyników.

import os
from src.whisper import Whisper
from src import config

class TranscriptionProcessor:
    """
    Klasa zarządzająca procesem transkrypcji plików audio.
    """
    def __init__(self):
        """
        Inicjalizuje procesor transkrypcji.
        """
        self.response_format = config.WHISPER_API_RESPONSE_FORMAT
        self.prompt = config.WHISPER_API_PROMPT
        self.temperature = config.WHISPER_API_TEMPERATURE

    def process_transcriptions(self):
        """
        Główna metoda klasy. Przetwarza pliki z listy `PROCESSING_LIST_FILE`,
        wykonuje transkrypcję i zarządza plikami stanu.
        """
        print("\nKrok 3: Rozpoczynanie transkrypcji plików...")

        # Wyczyść stary plik z wynikami, jeśli istnieje
        if os.path.exists(config.TRANSCRIPTIONS_FILE):
            os.remove(config.TRANSCRIPTIONS_FILE)

        # Wyczyść stary plik z przetworzonymi plikami
        if os.path.exists(config.PROCESSED_LIST_FILE):
            os.remove(config.PROCESSED_LIST_FILE)

        # Odczytaj listę plików do przetworzenia
        try:
            with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf8') as f:
                # Kopiujemy listę, aby móc ją modyfikować w pętli
                files_to_process = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            print("BŁĄD: Plik z listą do przetworzenia nie istnieje.")
            return

        # Tworzymy kopię, aby bezpiecznie iterować i usuwać elementy
        processing_queue = list(files_to_process)

        for audio_file in processing_queue:
            whisper = Whisper(audio_file)
            print(f"  Przetwarzanie pliku: {os.path.basename(audio_file)}")
            transcription = whisper.transcribe()

            if transcription:
                # Zapisz wynik transkrypcji
                with open(config.TRANSCRIPTIONS_FILE, 'a', encoding='utf8') as f:
                    f.write(f"{transcription.text}\n\n")
                print(f"    Sukces: Transkrypcja zapisana.")

                # Zaktualizuj pliki stanu
                # Dodaj do listy przetworzonych
                with open(config.PROCESSED_LIST_FILE, 'a', encoding='utf8') as f:
                    f.write(audio_file + '\n')

                # Usuń z listy do przetworzenia
                files_to_process.remove(audio_file)
                with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf8') as f:
                    for file_path in files_to_process:
                        f.write(file_path + '\n')
            else:
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

        print("\nZakończono proces transkrypcji.")
        print(f"Wszystkie transkrypcje zostały zapisane w: {config.TRANSCRIPTIONS_FILE}")