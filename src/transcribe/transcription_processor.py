import os
import threading
from src.whisper import Whisper
from src import config

class TranscriptionProcessor:
    """
    Klasa zarządzająca procesem transkrypcji plików audio z obsługą pauzy.
    """
    def __init__(self, pause_requested_event: threading.Event = None):
        """
        Inicjalizuje procesor transkrypcji.

        Args:
            pause_requested_event: Obiekt `threading.Event` do sygnalizowania żądania pauzy.
                                   Jeśli zostanie ustawiony, pętla zakończy się po bieżącym pliku.
        """
        self.response_format = config.WHISPER_API_RESPONSE_FORMAT
        self.prompt = config.WHISPER_API_PROMPT
        self.temperature = config.WHISPER_API_TEMPERATURE
        self.pause_requested_event = pause_requested_event

    def process_transcriptions(self):
        """
        Główna metoda klasy. Przetwarza pliki z listy `PROCESSING_LIST_FILE`,
        wykonuje transkrypcję i zarządza plikami stanu.
        Przerywa pracę, jeśli `pause_requested_event` jest ustawiony.
        """
        print("\nKrok 3: Rozpoczynanie lub wznawianie transkrypcji plików...")

        try:
            with open(config.PROCESSING_LIST_FILE, 'r', encoding='utf8') as f:
                files_to_process = [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            print("BŁĄD: Plik z listą do przetworzenia nie istnieje.")
            return

        while files_to_process:
            audio_file = files_to_process.pop(0)

            whisper = Whisper(audio_file)
            print(f"  Przetwarzanie pliku: {os.path.basename(audio_file)}")
            transcription = whisper.transcribe()

            if transcription:
                with open(config.TRANSCRIPTIONS_FILE, 'a', encoding='utf8') as f:
                    f.write(f"{transcription.text}\n\n")
                print(f"    Sukces: Transkrypcja zapisana.")

                with open(config.PROCESSED_LIST_FILE, 'a', encoding='utf8') as f:
                    f.write(audio_file + '\n')

                with open(config.PROCESSING_LIST_FILE, 'w', encoding='utf8') as f:
                    for file_path in files_to_process:
                        f.write(file_path + '\n')
            else:
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

            # Sprawdź, czy zażądano pauzy po zakończeniu przetwarzania pliku
            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break

        print("\nZakończono pętlę przetwarzania.")