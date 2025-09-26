import os
import threading
from src.whisper import Whisper
from src import database

class TranscriptionProcessor:
    """
    Zarządza procesem transkrypcji, pobierając pliki z bazy danych,
    przetwarzając je i zapisując wyniki z powrotem.
    """
    def __init__(self, pause_requested_event: threading.Event = None):
        """
        Inicjalizuje procesor.
        Args:
            pause_requested_event: `threading.Event` do sygnalizowania pauzy.
        """
        self.pause_requested_event = pause_requested_event

    def process_transcriptions(self):
        """
        Główna metoda. Pobiera pliki, które są załadowane, ale nieprzetworzone,
        wykonuje transkrypcję i aktualizuje bazę danych.
        """
        print("\nKrok 3: Rozpoczynanie transkrypcji plików...")

        # Pobierz wszystkie pliki do przetworzenia w jednej operacji
        all_files = {row['source_file_path']: row for row in database.get_all_files()}
        files_to_process = [
            f for f in all_files.values()
            if f['is_loaded'] and not f['is_processed']
        ]

        if not files_to_process:
            print("Brak plików oczekujących na transkrypcję.")
            return

        for file_data in files_to_process:
            source_path = file_data['source_file_path']
            tmp_path = file_data['tmp_file_path']

            if not tmp_path or not os.path.exists(tmp_path):
                print(f"    BŁĄD: Oczekiwany plik tymczasowy nie istnieje: {tmp_path}. Pomijanie.")
                continue

            print(f"  Przetwarzanie pliku: {os.path.basename(source_path)}")

            whisper = Whisper(tmp_path)
            transcription = whisper.transcribe()

            if transcription and hasattr(transcription, 'text'):
                database.update_file_transcription(source_path, transcription.text)
                print(f"    Sukces: Transkrypcja zapisana w bazie danych.")
            else:
                print(f"    Pominięto plik {os.path.basename(source_path)} z powodu błędu transkrypcji.")

            # Usuń tymczasowy plik .wav po przetworzeniu
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError as e:
                print(f"    OSTRZEŻENIE: Nie można usunąć tymczasowego pliku {tmp_path}: {e}")

            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break

        print("\nZakończono pętlę przetwarzania transkrypcji.")