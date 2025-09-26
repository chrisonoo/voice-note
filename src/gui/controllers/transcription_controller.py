import threading
from tkinter import messagebox
from src import database
from src.transcribe.transcription_processor import TranscriptionProcessor

class TranscriptionController:
    """
    Zarządza procesem transkrypcji w oparciu o stan w bazie danych.
    """
    
    def __init__(self, app):
        self.app = app
    
    def start_transcription_process(self):
        """
        Rozpoczyna proces transkrypcji dla plików oznaczonych jako 'is_loaded'.
        """
        if not database.get_files_to_process():
            messagebox.showwarning("Brak plików", "Brak plików wczytanych do przetworzenia.")
            return

        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()
        self.app.update_idletasks()

        self.app.pause_request_event.clear()
        self.app.processing_thread = threading.Thread(target=self._transcription_thread_worker, daemon=True)
        self.app.processing_thread.start()
        self.app.button_state_controller.update_ui_state()

    def pause_transcription(self):
        """Wysyła żądanie pauzy do wątku przetwarzającego."""
        self.app.pause_request_event.set()
        self.app.button_state_controller.update_ui_state()

    def resume_transcription(self):
        """Wycofuje żądanie pauzy."""
        self.app.pause_request_event.clear()
        self.app.button_state_controller.update_ui_state()

    def resume_interrupted_process(self):
        """
        Wznawia przerwany proces. W nowej logice jest to tożsame
        z normalnym uruchomieniem procesu, ponieważ stan jest w bazie danych.
        """
        if not database.get_files_to_process():
            messagebox.showinfo("Informacja", "Brak plików w kolejce do wznowienia.")
            self.app.button_state_controller.update_ui_state()
            return

        self.start_transcription_process()

    def _transcription_thread_worker(self):
        """Wątek roboczy do obsługi transkrypcji."""
        try:
            # The callback is a lambda that schedules the actual GUI update method
            # to be run on the main thread via app.after().
            progress_callback = lambda: self.app.after(0, self.app.on_transcription_progress)

            processor = TranscriptionProcessor(
                pause_requested_event=self.app.pause_request_event,
                on_progress_callback=progress_callback
            )
            processor.process_transcriptions()
        except Exception as e:
            self.app.after(0, lambda: messagebox.showerror("Błąd krytyczny", f"Wystąpił błąd: {e}"))
        finally:
            self.app.after(0, self.app.on_processing_finished)

    def on_processing_finished(self):
        """Obsługuje zakończenie procesu transkrypcji."""
        self.app.processing_thread = None
        self.app.pause_request_event.clear()
        self.app.button_state_controller.update_ui_state()
        self.app.refresh_all_views()
