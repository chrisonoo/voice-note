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
        with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf8') as f:
            files_to_process = [line.strip() for line in f.readlines()]

        for audio_file in files_to_process:
            whisper = Whisper(audio_file)
            print(f"  Przetwarzanie pliku: {os.path.basename(audio_file)}")
            transcription = whisper.transcribe()

            if transcription:
                # Zapisz wynik transkrypcji
                with open(config.TRANSCRIPTIONS_FILE, 'a', encoding='utf8') as f:
                    f.write(f"{transcription.text}\n\n")
                print(f"    Sukces: Transkrypcja zapisana.")

                # Zaktualizuj pliki stanu
                self._update_state_files(audio_file, files_to_process)
            else:
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

        print("\nZakończono proces transkrypcji.")
        print(f"Wszystkie transkrypcje zostały zapisane w: {config.TRANSCRIPTIONS_FILE}")

    def _update_state_files(self, processed_file, all_files):
        """
        Aktualizuje pliki stanu: dodaje plik do listy przetworzonych
        i usuwa go z listy do przetworzenia.
        """
        # Dodaj do listy przetworzonych
        with open(config.PROCESSED_LIST_FILE, 'a', encoding='utf8') as f:
            f.write(processed_file + '\n')

        # Usuń z listy do przetworzenia
        remaining_files = [f for f in all_files if f != processed_file]
        # Nadpisz plik z nową, skróconą listą
        with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf8') as f:
            for file_path in remaining_files:
                f.write(file_path + '\n')
        # Musimy zaktualizować `all_files` po usunięciu, aby kolejne iteracje działały poprawnie
        all_files.remove(processed_file)