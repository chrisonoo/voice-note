import os
import threading
from src.whisper import Whisper
from src import config

class TranscriptionProcessor:
    """
    Klasa zarządzająca procesem transkrypcji plików audio z obsługą pauzy.
    """
    def __init__(self, pause_requested_event: threading.Event = None, resume: bool = False):
        """
        Inicjalizuje procesor transkrypcji.

        Args:
            pause_requested_event: Obiekt `threading.Event` do sygnalizowania żądania pauzy.
                                   Jeśli zostanie ustawiony, pętla zakończy się po bieżącym pliku.
            resume (bool): Flaga wskazująca, czy proces jest wznawiany. Jeśli `True`,
                           pliki stanu nie zostaną wyczyszczone na starcie.
        """
        self.response_format = config.WHISPER_API_RESPONSE_FORMAT
        self.prompt = config.WHISPER_API_PROMPT
        self.temperature = config.WHISPER_API_TEMPERATURE
        self.pause_requested_event = pause_requested_event
        self.resume = resume

    def process_transcriptions(self):
        """
        Główna metoda klasy. Przetwarza pliki z listy `PROCESSING_LIST`,
        wykonuje transkrypcję i zarządza plikami stanu.
        Przerywa pracę, jeśli `pause_requested_event` jest ustawiony.
        """
        print("\nKrok 3: Rozpoczynanie lub wznawianie transkrypcji plików...")

        # Clear the processed and transcriptions lists only if it's a fresh start
        if not self.resume:
            for file_path in [config.PROCESSED_LIST, config.TRANSCRIPTIONS]:
                if os.path.exists(file_path):
                    os.remove(file_path)

        try:
            with open(config.PROCESSING_LIST, 'r', encoding='utf8') as f:
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
                # Ensure tmp directory exists before writing
                os.makedirs(os.path.dirname(config.TRANSCRIPTIONS), exist_ok=True)
                with open(config.TRANSCRIPTIONS, 'a', encoding='utf8') as f:
                    f.write(f"{transcription.text}\n\n")
                print(f"    Sukces: Transkrypcja zapisana.")

                os.makedirs(os.path.dirname(config.PROCESSED_LIST), exist_ok=True)
                with open(config.PROCESSED_LIST, 'a', encoding='utf8') as f:
                    f.write(audio_file + '\n')

                os.makedirs(os.path.dirname(config.PROCESSING_LIST), exist_ok=True)
                with open(config.PROCESSING_LIST, 'w', encoding='utf8') as f:
                    for file_path in files_to_process:
                        f.write(file_path + '\n')
            else:
                print(f"    Pominięto plik {audio_file} z powodu błędu transkrypcji.")

            # Sprawdź, czy zażądano pauzy po zakończeniu przetwarzania pliku
            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break

        print("\nZakończono pętlę przetwarzania.")