import os
import threading
from src.whisper import Whisper
from src import database

class TranscriptionProcessor:
    """
    Zarządza procesem transkrypcji, pobierając pliki z bazy danych,
    przetwarzając je i zapisując wyniki z powrotem.
    """
    def __init__(self, pause_requested_event: threading.Event = None, on_progress_callback=None):
        """
        Inicjalizuje procesor.
        Args:
            pause_requested_event: `threading.Event` do sygnalizowania pauzy.
            on_progress_callback: Funkcja zwrotna wywoływana po przetworzeniu każdego pliku.
        """
        self.pause_requested_event = pause_requested_event
        self.on_progress_callback = on_progress_callback

    def process_transcriptions(self):
        """
        Główna metoda. Pobiera pliki, które są załadowane, ale nieprzetworzone,
        wykonuje transkrypcję i aktualizuje bazę danych.
        """
        print("\nKrok 3: Rozpoczynanie transkrypcji plików...")

        files_to_process = database.get_files_to_process()

        if not files_to_process:
            print("Brak plików oczekujących na transkrypcję.")
            return

        for source_path in files_to_process:
            # Pobierz szczegóły pliku wewnątrz pętli, aby mieć pewność, że dane są aktualne
            with database.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT tmp_file_path FROM files WHERE source_file_path = ?", (source_path,))
                result = cursor.fetchone()

            if not result or not result['tmp_file_path']:
                 print(f"    BŁĄD: Brak ścieżki tymczasowej dla pliku: {source_path}. Pomijanie.")
                 continue

            tmp_path = result['tmp_file_path']

            if not os.path.exists(tmp_path):
                print(f"    BŁĄD: Oczekiwany plik tymczasowy nie istnieje: {tmp_path}. Pomijanie.")
                continue

            print(f"  Przetwarzanie pliku: {os.path.basename(source_path)}")

            whisper = Whisper(tmp_path)
            transcription = whisper.transcribe()

            if transcription and hasattr(transcription, 'text'):
                database.update_file_transcription(source_path, transcription.text)
                print(f"    Sukces: Transkrypcja zapisana w bazie danych.")

                # Wywołaj callback, jeśli został dostarczony
                if self.on_progress_callback:
                    self.on_progress_callback()
            else:
                print(f"    Pominięto plik {os.path.basename(source_path)} z powodu błędu transkrypcji.")

            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break

        print("\nZakończono pętlę przetwarzania transkrypcji.")