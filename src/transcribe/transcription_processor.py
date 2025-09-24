import os
import shutil
from src.whisper import Whisper
from src import config


class TranscriptionProcessor:
    def __init__(self):
        """
        Inicjalizuje procesor transkrypcji. Konfiguracja jest wczytywana
        z pliku config.py.
        """
        self.response_format = config.WHISPER_API_RESPONSE_FORMAT
        self.prompt = config.WHISPER_API_PROMPT
        self.temperature = config.WHISPER_API_TEMPERATURE

    def _prepare_transcription_list(self):
        """
        Tworzy listę plików do transkrypcji na podstawie zawartości
        katalogu wyjściowego (po konwersji).
        """
        print("\nKrok 3: Przygotowywanie listy plików do transkrypcji...")
        with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'w', encoding='utf-8') as f:
            for root, _, files in os.walk(config.OUTPUT_DIR):
                for file in files:
                    # Sprawdzamy, czy plik ma rozszerzenie .wav, bo tylko takie powinny być w folderze output
                    if file.lower().endswith(".wav"):
                        full_path = os.path.abspath(os.path.join(root, file))
                        f.write(full_path + '\n')

        # Kopiujemy listę plików do pliku śledzącego postęp
        shutil.copyfile(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, config.PROCESSING_LIST_FILE)
        print(f"Lista plików do transkrypcji została zapisana w: {config.AUDIO_LIST_TO_TRANSCRIBE_FILE}")

    def process_transcriptions(self):
        """
        Przetwarza pliki z listy, wykonuje transkrypcję i zarządza plikami stanu.
        """
        self._prepare_transcription_list()

        print("\nKrok 4: Rozpoczynanie transkrypcji plików...")

        with open(config.AUDIO_LIST_TO_TRANSCRIBE_FILE, 'r', encoding='utf8') as source_files:
            lines = source_files.readlines()

        # Czyszczenie pliku z wynikami przed rozpoczęciem
        if os.path.exists(config.TRANSCRIPTIONS_FILE):
            os.remove(config.TRANSCRIPTIONS_FILE)

        for line in lines:
            audio_file = line.strip()
            whisper = Whisper(audio_file)

            print(f"  Przetwarzanie pliku: {audio_file}")
            transcription = whisper.transcribe()

            if transcription:
                # Zapisujemy transkrypcję do pliku zbiorczego
                with open(config.TRANSCRIPTIONS_FILE, 'a', encoding='utf8') as f:
                    f.write(f"--- Transkrypcja dla: {os.path.basename(audio_file)} ---\n")
                    f.write(f"{transcription.text}\n\n")

                print(f"    Sukces: Transkrypcja zapisana.")

                # Aktualizujemy pliki stanu
                self._update_state_files(audio_file)
            else:
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

        print("\nZakończono proces transkrypcji.")
        print(f"Wszystkie transkrypcje zostały zapisane w: {config.TRANSCRIPTIONS_FILE}")

    def _update_state_files(self, audio_file):
        """
        Dodaje wpis do listy przetworzonych plików i usuwa z listy
        oczekujących na przetworzenie.
        """
        with open(config.PROCESSED_LIST_FILE, 'a', encoding='utf8') as processed_files:
            processed_files.write(audio_file + '\n')

        with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf8') as proc_file:
            processing_lines = proc_file.readlines()

        new_lines = [proc_line for proc_line in processing_lines if proc_line.strip() != audio_file]

        with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf8') as file:
            file.writelines(new_lines)