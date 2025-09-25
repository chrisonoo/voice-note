import os
import threading
from src.whisper import Whisper
from src import config, database

class TranscriptionProcessor:
    """
    Klasa zarządzająca procesem transkrypcji plików audio.
    Pobiera pliki z bazy danych, przetwarza je i zapisuje wyniki z powrotem do bazy.
    """
    def __init__(self, pause_requested_event: threading.Event = None):
        """
        Inicjalizuje procesor transkrypcji.

        Args:
            pause_requested_event: Obiekt `threading.Event` do sygnalizowania żądania pauzy.
                                   Jeśli zostanie ustawiony, pętla zakończy się po bieżącym pliku.
        """
        self.pause_requested_event = pause_requested_event

    def _get_wav_path(self, original_path):
        """Generuje ścieżkę do pliku .wav na podstawie oryginalnej ścieżki."""
        base_name = os.path.basename(original_path)
        standardized_name, _ = os.path.splitext(base_name.lower().replace(' ', '_'))
        output_filename = f"{standardized_name}.wav"
        return os.path.join(config.OUTPUT_DIR, output_filename)

    def process_transcriptions(self):
        """
        Główna metoda klasy. Pobiera pliki ze statusem 'encoded' z bazy danych,
        wykonuje transkrypcję i zarządza statusem plików w bazie.
        Przerywa pracę, jeśli `pause_requested_event` jest ustawiony.
        """
        print("\nKrok 3: Rozpoczynanie transkrypcji plików...")

        files_to_process = database.get_files_by_status('encoded')

        if not files_to_process:
            print("Brak plików oczekujących na transkrypcję.")
            return

        for original_path in files_to_process:
            # Zmiana statusu na 'processing', aby uniknąć podwójnego przetwarzania
            database.update_file_status(original_path, 'processing')

            wav_path = self._get_wav_path(original_path)

            if not os.path.exists(wav_path):
                print(f"    BŁĄD: Oczekiwany plik .wav nie istnieje: {wav_path}. Pomijanie.")
                database.update_file_status(original_path, 'error')
                continue

            print(f"  Przetwarzanie pliku: {os.path.basename(original_path)}")

            whisper = Whisper(wav_path)
            transcription = whisper.transcribe()

            if transcription and hasattr(transcription, 'text'):
                database.update_transcription(original_path, transcription.text)
                print(f"    Sukces: Transkrypcja zapisana w bazie danych.")
            else:
                database.update_file_status(original_path, 'transcription_error')
                print(f"    Pominięto plik {os.path.basename(original_path)} z powodu błędu transkrypcji.")

            # Usuń tymczasowy plik .wav po przetworzeniu
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except OSError as e:
                print(f"    OSTRZEŻENIE: Nie można usunąć tymczasowego pliku {wav_path}: {e}")

            # Sprawdź, czy zażądano pauzy po zakończeniu przetwarzania pliku
            if self.pause_requested_event and self.pause_requested_event.is_set():
                print("Żądanie pauzy wykryte. Zatrzymywanie przetwarzania...")
                break

        print("\nZakończono pętlę przetwarzania transkrypcji.")